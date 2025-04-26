# Rui Santos & Sara Santos - Random Nerd Tutorials
# Complete project details at https://RandomNerdTutorials.com/raspberry-pi-pico-neo-6m-micropython/

import machine
from time import ticks_ms, ticks_diff
from micropyGPS import MicropyGPS

# Setup GPS UART
gps_serial = machine.UART(1, baudrate=9600, tx=4, rx=5)
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

def raw_to_temp_c(temp_raw):
    # Placeholder: adjust for your sensor
    # Example: 0x666 = 0°C, 0xE666 = 100°C
    return (temp_raw - 0x666) * (100.0 / (0xE666 - 0x666))

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

gps_buffer = b""
last_print = ticks_ms()

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
        temp_c = raw_to_temp_c(temp_raw) if temp_raw is not None else None
        airspeed = airspeed_from_pressures(pitot_pa, STATIC_PRESSURE_PA) if pitot_pa is not None else None
    except Exception as e:
        pitot_pa = None
        temp_c = None
        airspeed = None

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
    else:
        lat = "N/A"
        lon = "N/A"

    # Print GPS elevation (altitude)
    if my_gps.altitude is not None:
        elevation_str = "{:.2f} m".format(my_gps.altitude)
    else:
        elevation_str = "N/A"

    airspeed_str = "{:.2f} m/s".format(airspeed) if airspeed is not None else "N/A"
    temp_str = "{:.2f} C".format(temp_c) if temp_c is not None else "N/A"

    # Get number of satellites
    num_sats = my_gps.satellites_in_use if hasattr(my_gps, "satellites_in_use") and my_gps.satellites_in_use is not None else "N/A"

    print("Time: {} | Lat: {} | Lon: {} | Elevation: {} | Airspeed: {} | Temp: {} | Sats: {}".format(
        gps_time, lat, lon, elevation_str, airspeed_str, temp_str, num_sats
    ))
