import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import contextily as ctx
from matplotlib.colors import LinearSegmentedColormap
import matplotlib.patheffects as pe

# Read the CSV file, skipping any blank lines
df = pd.read_csv('airspeed.csv', skip_blank_lines=True)

# Drop rows where latitude or longitude is missing
df = df.dropna(subset=['latitude', 'longitude'])

# Convert latitude and longitude to float (in case they are read as strings)
df['latitude'] = df['latitude'].astype(float)
df['longitude'] = df['longitude'].astype(float)

# Smooth latitude and longitude using a rolling average with window=15 (instead of 5)
df['lat_smooth'] = df['latitude'].rolling(window=15, min_periods=1).mean()
df['lon_smooth'] = df['longitude'].rolling(window=15, min_periods=1).mean()

# Parse time to seconds since start
def time_to_seconds(t):
    h, m, s = t.split(':')
    return int(h) * 3600 + int(m) * 60 + float(s)

df['time_sec'] = df['time'].apply(time_to_seconds)
df['time_smooth'] = df['time_sec'].rolling(window=15, min_periods=1).mean()

# Haversine formula to compute distance in meters
def haversine(lat1, lon1, lat2, lon2):
    R = 6371000  # Earth radius in meters
    phi1 = np.radians(lat1)
    phi2 = np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lon2 - lon1)
    a = np.sin(dphi/2.0)**2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda/2.0)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
    return R * c

# Calculate ground speed and track
ground_speeds = [np.nan]
tracks = [np.nan]

for i in range(1, len(df)):
    lat1, lon1 = df.loc[i-1, 'lat_smooth'], df.loc[i-1, 'lon_smooth']
    lat2, lon2 = df.loc[i, 'lat_smooth'], df.loc[i, 'lon_smooth']
    t1, t2 = df.loc[i-1, 'time_smooth'], df.loc[i, 'time_smooth']
    dt = t2 - t1
    if dt == 0:
        ground_speeds.append(np.nan)
        tracks.append(np.nan)
        continue
    # Distance in meters
    dist = haversine(lat1, lon1, lat2, lon2)
    speed = dist / dt  # m/s

    # Track (bearing) in degrees
    dlon = np.radians(lon2 - lon1)
    y = np.sin(dlon) * np.cos(np.radians(lat2))
    x = np.cos(np.radians(lat1)) * np.sin(np.radians(lat2)) - \
        np.sin(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.cos(dlon)
    bearing = np.degrees(np.arctan2(y, x))
    bearing = (bearing + 360) % 360

    ground_speeds.append(speed)
    tracks.append(bearing)

df['ground_speed_mps'] = ground_speeds
df['track_deg'] = tracks

# Create a table of ground speed and track
speed_track_table = df[['time', 'ground_speed_mps', 'track_deg']].copy()

# Save timestamp, ground speed and track to a CSV file
speed_track_table.to_csv('ground_speed_track.csv', index=False)

# Calculate estimated route based on ground speed and track
# Start from the first known position
estimated_lats = [df['latitude'].iloc[0]]
estimated_lons = [df['longitude'].iloc[0]]

for i in range(1, len(df)):
    if np.isnan(df['ground_speed_mps'].iloc[i]) or np.isnan(df['track_deg'].iloc[i]):
        # If data is missing, just use the previous point
        estimated_lats.append(estimated_lats[-1])
        estimated_lons.append(estimated_lons[-1])
        continue
    
    # Get time difference
    dt = df['time_sec'].iloc[i] - df['time_sec'].iloc[i-1]
    if dt <= 0:
        estimated_lats.append(estimated_lats[-1])
        estimated_lons.append(estimated_lons[-1])
        continue
    
    # Get speed and bearing
    speed = df['ground_speed_mps'].iloc[i]
    bearing_rad = np.radians(df['track_deg'].iloc[i])
    
    # Calculate distance traveled
    distance = speed * dt
    
    # Current position
    lat1 = np.radians(estimated_lats[-1])
    lon1 = np.radians(estimated_lons[-1])
    
    # Earth radius in meters
    R = 6371000
    
    # Calculate new position
    lat2 = np.arcsin(np.sin(lat1) * np.cos(distance/R) + 
                     np.cos(lat1) * np.sin(distance/R) * np.cos(bearing_rad))
    
    lon2 = lon1 + np.arctan2(np.sin(bearing_rad) * np.sin(distance/R) * np.cos(lat1),
                             np.cos(distance/R) - np.sin(lat1) * np.sin(lat2))
    
    # Convert back to degrees
    estimated_lats.append(np.degrees(lat2))
    estimated_lons.append(np.degrees(lon2))

df['estimated_lat'] = estimated_lats
df['estimated_lon'] = estimated_lons

# Plot the GPS track on a street map
fig, ax = plt.subplots(figsize=(12, 12), dpi=150)

# Plot the raw GPS data as a thin line
ax.plot(df['longitude'], df['latitude'], '-', color='red', linewidth=1, alpha=0.7, 
        label='Raw GPS', path_effects=[pe.Stroke(linewidth=2, foreground='white'), pe.Normal()])

# Plot the smoothed route with a thicker line
ax.plot(df['lon_smooth'], df['lat_smooth'], '-', color='blue', linewidth=2.5, 
        label='Smoothed Path (15-point avg)', path_effects=[pe.Stroke(linewidth=3.5, foreground='white'), pe.Normal()])

# Plot the estimated route
ax.plot(df['estimated_lon'], df['estimated_lat'], '-', color='green', linewidth=2, 
        label='Estimated Path (from speed/track)', path_effects=[pe.Stroke(linewidth=3, foreground='white'), pe.Normal()])

# Add basemap
ctx.add_basemap(ax, crs='EPSG:4326', source=ctx.providers.OpenStreetMap.Mapnik)

# Set plot limits with a small buffer
buffer = 0.0005  # Adjust as needed
min_lon, max_lon = df['longitude'].min() - buffer, df['longitude'].max() + buffer
min_lat, max_lat = df['latitude'].min() - buffer, df['latitude'].max() + buffer
ax.set_xlim(min_lon, max_lon)
ax.set_ylim(min_lat, max_lat)

# Add title and legend
ax.set_title('GPS Track with Smoothed and Estimated Paths', fontsize=14)
ax.legend(loc='upper right', frameon=True, framealpha=0.9)

# Remove axis labels as they're not needed with the map
ax.set_xlabel('')
ax.set_ylabel('')

plt.tight_layout()
plt.savefig('gps_track_map.png', dpi=150, bbox_inches='tight')

# Calculate the difference between airspeed and ground speed
df['speed_difference'] = df['airspeed'] - df['ground_speed_mps']

# Normalize time to start at 0 for better readability
start_time = df['time_sec'].min()
df['time_sec_normalized'] = df['time_sec'] - start_time

# Create a time series plot for airspeed, ground speed, and their difference (all as rolling averages)
plt.figure(figsize=(12, 8), dpi=150)

# Set rolling window size
window_size = 200

# Compute rolling averages for airspeed, ground speed, and their difference
df['airspeed_avg'] = df['airspeed'].rolling(window=window_size, center=True).mean()
df['ground_speed_avg'] = df['ground_speed_mps'].rolling(window=window_size, center=True).mean()
df['speed_difference_avg'] = df['speed_difference'].rolling(window=window_size, center=True).mean()

# Fill NaN values at the beginning and end of the rolling average
df['airspeed_avg'] = df['airspeed_avg'].fillna(df['airspeed'])
df['ground_speed_avg'] = df['ground_speed_avg'].fillna(df['ground_speed_mps'])
df['speed_difference_avg'] = df['speed_difference_avg'].fillna(df['speed_difference'])

# Plot rolling average airspeed and ground speed
plt.subplot(2, 1, 1)
plt.plot(df['time_sec_normalized'], df['airspeed_avg'], '-', color='blue', label='Airspeed (rolling avg)')
plt.plot(df['time_sec_normalized'], df['ground_speed_avg'], '-', color='orange', label='Ground Speed (rolling avg)')
plt.xlabel('Time (seconds from start)')
plt.ylabel('Speed (m/s)')
plt.title('Airspeed vs Ground Speed (Rolling Averages)')
plt.grid(True)
plt.legend()

# Plot the rolling average difference, offsetting by its mean
mean_diff = df['speed_difference_avg'].mean()
plt.subplot(2, 1, 2)
plt.plot(
    df['time_sec_normalized'],
    df['speed_difference_avg'] - mean_diff,
    '-', color='red',
    label='Airspeed - Ground Speed (rolling avg, mean offset)'
)
plt.axhline(y=0, color='black', linestyle='--', alpha=0.7)
plt.xlabel('Time (seconds from start)')
plt.ylabel('Difference (m/s, mean offset)')
plt.title('Airspeed - Ground Speed (Rolling Average, Mean Offset)')
plt.grid(True)
plt.legend()

plt.tight_layout()
plt.savefig('speed_comparison.png', dpi=150, bbox_inches='tight')
plt.show()
