import machine
import time
from math import sqrt

PITOT_ADDR = 0x28

# Initialize I2C on I2C(0), SDA=GPIO8, SCL=GPIO9
i2c = machine.I2C(0, sda=machine.Pin(8), scl=machine.Pin(9), freq=400000)

def parse_pressure_diff(data):
    # Data is 4 bytes: [P_MSB, P_LSB, T_MSB, T_LSB]
    if len(data) != 4:
        return 0
    pressure_raw = (data[0] << 8) | data[1]
    # For Honeywell HSC/SSC: 1638 (min) to 14745 (max) = 0 to 1 psi
    # 1 psi = 6894.76 Pa
    if pressure_raw < 1638:
        pressure_raw = 1638
    if pressure_raw > 14745:
        pressure_raw = 14745
    psi = (pressure_raw - 1638) * (1.0 / (14745 - 1638))
    pa = psi * 6894.76
    return pa

def airspeed_from_pressure_diff(pressure_diff_pa, rho=1.225):
    # v = sqrt(2 * dp / rho)
    if pressure_diff_pa is None or pressure_diff_pa < 0:
        return 0
    v = sqrt(2 * pressure_diff_pa / rho)
    return v

# Calibration: collect first 5 readings to determine zero offset
calibration_readings = []
calibrated = False
zero_offset = 0.0
calibration_count = 5

print("Calibrating... Please keep sensor at rest.")

while not calibrated:
    try:
        data = i2c.readfrom(PITOT_ADDR, 4)
        pa = parse_pressure_diff(data)
        if pa is not None:
            calibration_readings.append(pa)
            print("Calibration reading {}: {:.2f} Pa".format(len(calibration_readings), pa))
        else:
            print("Calibration reading {}: 0".format(len(calibration_readings)+1))
    except Exception as e:
        print("I2C read error during calibration:", e)
    time.sleep(0.05)
    if len(calibration_readings) >= calibration_count:
        zero_offset = sum(calibration_readings) / len(calibration_readings)
        calibrated = True
        print("Calibration complete. Zero offset: {:.2f} Pa".format(zero_offset))

while True:
    try:
        # Read 4 bytes from Pitot sensor at 0x28
        data = i2c.readfrom(PITOT_ADDR, 4)
        pressure_diff_pa = parse_pressure_diff(data)
        if pressure_diff_pa is not None:
            # Subtract zero offset
            pressure_diff_pa -= zero_offset
        airspeed = airspeed_from_pressure_diff(pressure_diff_pa)
        if airspeed is not None:
            print("Airspeed: {:.2f} m/s".format(airspeed))
        else:
            print("Airspeed: 0")
    except Exception as e:
        print("I2C read error:", e)
    time.sleep(0.01)
