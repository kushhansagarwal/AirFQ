# Rui Santos & Sara Santos - Random Nerd Tutorials
# Complete project details at https://RandomNerdTutorials.com/raspberry-pi-pico-neo-6m-micropython/

import machine
from time import ticks_ms, ticks_diff, sleep_ms
from micropyGPS import MicropyGPS

# SD card setup
import sdcard
import uos

# Assign chip select (CS) pin (and start it high)
cs = machine.Pin(1, machine.Pin.OUT)
# Intialize SPI peripheral (start with 1 MHz)
spi = machine.SPI(0,
                  baudrate=1000000,
                  polarity=0,
                  phase=0,
                  bits=8,
                  firstbit=machine.SPI.MSB,
                  sck=machine.Pin(2),
                  mosi=machine.Pin(3),
                  miso=machine.Pin(4))
# Initialize SD card
sd = sdcard.SDCard(spi, cs)
# Mount filesystem
vfs = uos.VfsFat(sd)
uos.mount(vfs, "/sd")

# Setup GPS UART
gps_serial = machine.UART(0, baudrate=9600, tx=16, rx=17)
my_gps = MicropyGPS(location_formatting='dd')  # Use decimal degrees

# Setup Pitot tube I2C
PITOT_ADDR = 0x28
sda = machine.Pin(8)
scl = machine.Pin(9)
i2c = machine.I2C(0, sda=sda, scl=scl, freq=400000)

# Constants for airspeed calculation
SEA_LEVEL_PRESSURE_PA = 101325  # Pa
SEA_LEVEL_TEMP_K = 288.15       # K
ELEVATION_FT = 440
ELEVATION_M = ELEVATION_FT * 0.3048

def pressure_at_elevation(elevation_m):
    L = 0.0065
    R = 8.31447
    M = 0.0289644
    g = 9.80665
    T0 = SEA_LEVEL_TEMP_K
    P0 = SEA_LEVEL_PRESSURE_PA
    return P0 * (1 - (L * elevation_m) / T0) ** (g * M / (R * L))

STATIC_PRESSURE_PA = pressure_at_elevation(ELEVATION_M)

def parse_pitot_data(data):
    if len(data) != 4:
        return None, None
    pressure_raw = (data[0] << 8) | data[1]
    temp_raw = (data[2] << 8) | data[3]
    return pressure_raw, temp_raw

def raw_to_pressure_pa(pressure_raw):
    # Example conversion for Honeywell sensor (adjust for your sensor)
    # Output: 1638 (min) to 14745 (max) = 0 to 1 psi
    # 1 psi = 6894.76 Pa
    if pressure_raw < 1638:
        pressure_raw = 1638
    if pressure_raw > 14745:
        pressure_raw = 14745
    psi = (pressure_raw - 1638) * (1.0 / (14745 - 1638))
    return psi * 6894.76

# Remove raw_to_temp_c and use onboard temperature sensor instead

def airspeed_from_pressures(pitot_pa, static_pa):
    # Calculate airspeed in m/s from differential pressure
    # v = sqrt(2 * (pitot_pa - static_pa) / rho)
    # Assume rho = 1.225 kg/m^3 (sea level, 15°C)
    rho = 1.225
    dp = pitot_pa - static_pa
    if dp < 0:
        dp = 0
    from math import sqrt
    return sqrt(2 * dp / rho)

# Function to read onboard temperature sensor (RP2040)
def read_onboard_temp_c():
    # The onboard temperature sensor is connected to ADC4
    sensor = machine.ADC(4)
    reading = sensor.read_u16()  # 16-bit value (0-65535)
    # Convert to voltage (3.3V reference)
    voltage = reading * 3.3 / 65535
    # According to RP2040 datasheet:
    # Temperature (in °C) = 27 - (V_sensor - 0.706)/0.001721
    temp_c = 27 - (voltage - 0.706) / 0.001721
    return temp_c

gps_buffer = b""
last_print = ticks_ms()
last_save = ticks_ms()
csv_file_path = "/sd/data_log.csv"
csv_header = "time,latitude,longitude,elevation,airspeed,temp,satellites\n"

# Setup LED for blink on write
led = machine.Pin("LED", machine.Pin.OUT)
led.off()

# Write CSV header if file does not exist
try:
    uos.stat(csv_file_path)
except OSError:
    with open(csv_file_path, "w") as f:
        f.write(csv_header)

while True:
    # --- GPS update ---
    while gps_serial.any():
        c = gps_serial.read(1)
        if c:
            my_gps.update(chr(c[0]))

    # --- Pitot tube read ---
    try:
        pitot_data = i2c.readfrom(PITOT_ADDR, 4)
        pressure_raw, temp_raw = parse_pitot_data(pitot_data)
        pitot_pa = raw_to_pressure_pa(pressure_raw) if pressure_raw is not None else None
        # temp_c = raw_to_temp_c(temp_raw) if temp_raw is not None else None  # Remove this line
        airspeed = airspeed_from_pressures(pitot_pa, STATIC_PRESSURE_PA) if pitot_pa is not None else None
    except Exception as e:
        pitot_pa = None
        # temp_c = None  # Remove this line
        airspeed = None

    # --- Onboard temperature read ---
    temp_c = read_onboard_temp_c()

    # --- Print as fast as possible ---
    # Get time, location, and elevation from GPS
    gps_time = "{:02}:{:02}:{:02}".format(*my_gps.timestamp) if my_gps.timestamp[0] is not None else "??:??:??"
    # Use decimal degrees for latitude and longitude, and print correct N/S/E/W
    if my_gps.latitude[0] is not None and my_gps.longitude[0] is not None:
        lat_val = my_gps.latitude[0]
        lat_dir = my_gps.latitude[1]
        lon_val = my_gps.longitude[0]
        lon_dir = my_gps.longitude[1]
        # Ensure sign and direction are consistent
        if lat_dir == 'S' and lat_val > 0:
            lat_val = -lat_val
        if lat_dir == 'N' and lat_val < 0:
            lat_val = -lat_val
        if lon_dir == 'W' and lon_val > 0:
            lon_val = -lon_val
        if lon_dir == 'E' and lon_val < 0:
            lon_val = -lon_val
        lat = "{:.8f} {}".format(abs(lat_val), lat_dir)
        lon = "{:.8f} {}".format(abs(lon_val), lon_dir)
        lat_csv = "{:.8f}".format(lat_val)
        lon_csv = "{:.8f}".format(lon_val)
    else:
        lat = "N/A"
        lon = "N/A"
        lat_csv = ""
        lon_csv = ""

    # Print GPS elevation (altitude)
    if my_gps.altitude is not None:
        elevation_str = "{:.2f} m".format(my_gps.altitude)
        elevation_csv = "{:.2f}".format(my_gps.altitude)
    else:
        elevation_str = "N/A"
        elevation_csv = ""

    airspeed_str = "{:.2f} m/s".format(airspeed) if airspeed is not None else "N/A"
    airspeed_csv = "{:.2f}".format(airspeed) if airspeed is not None else ""
    temp_str = "{:.2f} C".format(temp_c) if temp_c is not None else "N/A"
    temp_csv = "{:.2f}".format(temp_c) if temp_c is not None else ""

    # Get number of satellites
    num_sats = my_gps.satellites_in_use if hasattr(my_gps, "satellites_in_use") and my_gps.satellites_in_use is not None else "N/A"
    num_sats_csv = str(num_sats) if num_sats != "N/A" else ""

    print("Time: {} | Lat: {} | Lon: {} | Elevation: {} | Airspeed: {} | Temp: {} | Sats: {}".format(
        gps_time, lat, lon, elevation_str, airspeed_str, temp_str, num_sats
    ))

    # --- Save to CSV once per second ---
    now = ticks_ms()
    if ticks_diff(now, last_save) >= 1000:
        # Compose CSV line
        csv_line = "{},{},{},{},{},{},{}\n".format(
            gps_time, lat_csv, lon_csv, elevation_csv, airspeed_csv, temp_csv, num_sats_csv
        )
        try:
            with open(csv_file_path, "a") as f:
                f.write(csv_line)
            # Blink LED for 100ms to indicate data written
            led.on()
            sleep_ms(100)
            led.off()
        except Exception as e:
            print("SD write error:", e)
        last_save = now
