import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Read the airspeed CSV file
df = pd.read_csv('airspeed.csv', skip_blank_lines=True)

# Use time_ms column instead of converting time
# Convert milliseconds to seconds for plotting
df['time_sec'] = df['time_ms'] / 1000

# Normalize time to start at 0
start_time = df['time_sec'].min()
df['time_sec_normalized'] = df['time_sec'] - start_time

# Plot time vs airspeed
plt.figure(figsize=(10, 6))
plt.plot(df['time_sec_normalized'], df['airspeed'], '-o', markersize=2)
plt.xlabel('Time (seconds)')
plt.ylabel('Airspeed (m/s)')
plt.title('Airspeed vs Time')
plt.grid(True)
plt.tight_layout()
plt.show()
