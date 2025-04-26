import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import contextily as ctx
import matplotlib.patheffects as pe

# Read the ground speed and track data
df = pd.read_csv('derived.csv')

# Initialize arrays for estimated positions
estimated_lats = []
estimated_lons = []

# Set a starting position (you may want to adjust this based on your data)
# Using a reasonable starting point based on the context
start_lat = 34.07157135
start_lon = -118.45204163

estimated_lats.append(start_lat)
estimated_lons.append(start_lon)

# Parse time to seconds since start
def time_to_seconds(t):
    h, m, s = t.split(':')
    return int(h) * 3600 + int(m) * 60 + float(s)

df['time_sec'] = df['time'].apply(time_to_seconds)

# Reconstruct the path using ground speed and track
for i in range(1, len(df)):
    # Skip if time is the same as previous record
    if i > 0 and df['time_sec'].iloc[i] == df['time_sec'].iloc[i-1]:
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

# Add the estimated positions to the dataframe
df['estimated_lat'] = estimated_lats
df['estimated_lon'] = estimated_lons

# Plot the reconstructed path
fig, ax = plt.subplots(figsize=(12, 12), dpi=150)

# Plot the reconstructed route
ax.plot(df['estimated_lon'], df['estimated_lat'], '-', color='green', linewidth=2.5, 
        label='Reconstructed Path', path_effects=[pe.Stroke(linewidth=3.5, foreground='white'), pe.Normal()])

# Add basemap
ctx.add_basemap(ax, crs='EPSG:4326', source=ctx.providers.OpenStreetMap.Mapnik)

# Set plot limits with a small buffer
buffer = 0.0005  # Adjust as needed
min_lon, max_lon = min(df['estimated_lon']) - buffer, max(df['estimated_lon']) + buffer
min_lat, max_lat = min(df['estimated_lat']) - buffer, max(df['estimated_lat']) + buffer
ax.set_xlim(min_lon, max_lon)
ax.set_ylim(min_lat, max_lat)

# Add title and legend
ax.set_title('Reconstructed Path from Ground Speed and Track', fontsize=14)
ax.legend(loc='upper right', frameon=True, framealpha=0.9)

# Remove axis labels as they're not needed with the map
ax.set_xlabel('')
ax.set_ylabel('')

plt.tight_layout()
plt.savefig('reconstructed_path.png', dpi=150, bbox_inches='tight')
plt.show()

print(f"Path reconstructed with {len(df)} points")
print(f"Starting position: {start_lat}, {start_lon}")
print(f"Ending position: {estimated_lats[-1]}, {estimated_lons[-1]}")
