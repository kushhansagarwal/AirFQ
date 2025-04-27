import network
import urequests
import machine
import time
import gc
from math import sqrt

# --- GPS setup (same as logger.py) ---
from micropyGPS import MicropyGPS

# Setup GPS UART (same pins as logger.py)
gps_serial = machine.UART(0, baudrate=9600, tx=16, rx=17)
my_gps = MicropyGPS(location_formatting='dd')  # Use decimal degrees

# Connect to WiFi network
def connect_wifi(ssid, password):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print('Connecting to network {}...'.format(ssid))
        wlan.connect(ssid, password)
        while not wlan.isconnected():
            pass
    print('Network connected:', wlan.ifconfig())

connect_wifi("UCLA_RES_IOT", "RvE{7;?{")

url = "https://airfq-api.vercel.app/publish"

# I2C setup for pitot sensor (0x28)
PITOT_ADDR = 0x28
sda = machine.Pin(8)
scl = machine.Pin(9)
i2c = machine.I2C(0, sda=sda, scl=scl, freq=400000)

# Calibration for zero offset
zero_offset = 0
calibration_readings = []
calibration_count = 5
calibrated = False

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

def airspeed_from_pressures(pressure_diff_pa):
    # Calculate airspeed in m/s from differential pressure
    # v = sqrt(2 * dp / rho)
    # Assume rho = 1.225 kg/m^3 (sea level, 15°C)
    if pressure_diff_pa is None or pressure_diff_pa < 0:
        return 0
    rho = 1.225
    return sqrt(2 * pressure_diff_pa / rho)

# Calibrate pitot sensor at rest
print("Calibrating pitot sensor... Keep at rest.")
while not calibrated:
    try:
        pitot_data = i2c.readfrom(PITOT_ADDR, 4)
        pressure_raw, _ = parse_pitot_data(pitot_data)
        if pressure_raw is not None:
            pressure_pa = raw_to_pressure_pa(pressure_raw)
            calibration_readings.append(pressure_pa)
            print("Calibration reading {}: {:.2f} Pa".format(len(calibration_readings), pressure_pa))
            if len(calibration_readings) >= calibration_count:
                zero_offset = sum(calibration_readings) / len(calibration_readings)
                calibrated = True
                print("Calibration complete. Zero offset: {:.2f} Pa".format(zero_offset))
    except Exception as e:
        print("Calibration error:", e)
    time.sleep(0.1)

# --- Batch send after 30 samples, as fast as possible ---
batch = []

# Initialize timestamp relative to start
t_start = time.ticks_ms()

while True:
    # Always update GPS parser (not strictly needed for airspeed, but keep for completeness)
    while gps_serial.any():
        c = gps_serial.read(1)
        if c:
            my_gps.update(chr(c[0]))

    try:
        pitot_data = i2c.readfrom(PITOT_ADDR, 4)
        pressure_raw, temp_raw = parse_pitot_data(pitot_data)
        pitot_pa = raw_to_pressure_pa(pressure_raw) if pressure_raw is not None else None
        if pitot_pa is not None:
            pitot_pa -= zero_offset
        airspeed = airspeed_from_pressures(pitot_pa) if pitot_pa is not None else None
    except Exception as e:
        print("Pitot read error:", e)
        airspeed = None

    # Record timestamp relative to start (ms)
    now = time.ticks_ms()
    timestamp = time.ticks_diff(now, t_start)

    batch.append({
        "timestamp": timestamp,
        "airspeed": airspeed if airspeed is not None else ""
    })

    # Print every 15 datapoints
    if len(batch) % 15 == 0:
        print("Collected {} datapoints".format(len(batch)))

    # Send batch when we have 30 samples
    if len(batch) >= 30:
        data = {"data": batch}
        try:
            resp = urequests.post(url, json=data)
            resp.close()
            del resp
            print("Sent batch of 30 readings")
        except Exception as e:
            print("POST error:", e)

        batch = []  # Clear batch after sending
        gc.collect()

    time.sleep(0.001)  # Tiny sleep to avoid busy waiting, but as fast as possible
