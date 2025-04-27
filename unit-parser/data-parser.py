import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import contextily as ctx
from matplotlib.colors import Normalize
import matplotlib.patheffects as pe
from matplotlib.collections import LineCollection

# Read the airspeed CSV file, skipping any blank lines
df = pd.read_csv('airspeed.csv', skip_blank_lines=True)

# Drop rows where latitude or longitude is missing
df = df.dropna(subset=['latitude', 'longitude'])

# Convert latitude and longitude to float (in case they are read as strings)
df['latitude'] = df['latitude'].astype(float)
df['longitude'] = df['longitude'].astype(float)

# Smooth latitude and longitude using a rolling average with window=15
df['lat_smooth'] = df['latitude'].rolling(window=15, min_periods=1).mean()
df['lon_smooth'] = df['longitude'].rolling(window=15, min_periods=1).mean()

# --- Also save the ground speed and heading (track) ---

# Read ground speed and heading from ground_speed_track.csv
gs_df = pd.read_csv('ground_speed_track.csv', skip_blank_lines=True)

# Try to align by time if possible, otherwise just add as columns (assuming same length/order)
if 'time' in df.columns and 'time' in gs_df.columns:
    # Merge on time, keeping only rows with matching times
    merged = pd.merge(df, gs_df, on='time', how='left', suffixes=('', '_gs'))
    df['ground_speed_mps'] = merged['ground_speed_mps']
    df['track_deg'] = merged['track_deg']
else:
    # If no time column or not matching, just add as columns by index
    # (Assume same order/length, otherwise will get NaNs)
    df['ground_speed_mps'] = gs_df['ground_speed_mps'] if 'ground_speed_mps' in gs_df.columns else np.nan
    df['track_deg'] = gs_df['track_deg'] if 'track_deg' in gs_df.columns else np.nan

# Save the combined DataFrame with ground speed and heading to a new CSV
df.to_csv('airspeed_with_groundspeed_heading.csv', index=False)

# --- Reconstruct track from ground speed and heading ---

def reconstruct_track(lat0, lon0, ground_speed, heading_deg, dt):
    """
    Reconstructs a track from initial lat/lon, ground speed (m/s), heading (deg), and time step (s).
    Returns arrays of latitude and longitude.
    """
    R = 6378137.0  # Earth radius in meters
    lat = [lat0]
    lon = [lon0]
    for i in range(1, len(ground_speed)):
        gs = ground_speed[i-1]
        hdg = heading_deg[i-1]
        if np.isnan(gs) or np.isnan(hdg) or np.isnan(dt[i-1]):
            lat.append(lat[-1])
            lon.append(lon[-1])
            continue
        theta = np.deg2rad(hdg)
        d = gs * dt[i-1]
        lat1 = np.deg2rad(lat[-1])
        lon1 = np.deg2rad(lon[-1])
        # Haversine direct formula
        lat2 = np.arcsin(np.sin(lat1) * np.cos(d / R) +
                         np.cos(lat1) * np.sin(d / R) * np.cos(theta))
        lon2 = lon1 + np.arctan2(np.sin(theta) * np.sin(d / R) * np.cos(lat1),
                                 np.cos(d / R) - np.sin(lat1) * np.sin(lat2))
        lat.append(np.rad2deg(lat2))
        lon.append(np.rad2deg(lon2))
    return np.array(lat), np.array(lon)

# --- Compute time deltas for reconstruction ---
# Try to get time as seconds
def parse_time(t):
    # Try HH:MM:SS or seconds
    try:
        if isinstance(t, str) and ':' in t:
            h, m, s = [float(x) for x in t.split(':')]
            return h * 3600 + m * 60 + s
        else:
            return float(t)
    except Exception:
        return np.nan

if 'time' in df.columns:
    time_sec = df['time'].apply(parse_time).values
    dt = np.diff(time_sec, prepend=time_sec[0])
    # If dt is zero or negative, set to median positive dt
    median_dt = np.median(dt[dt > 0]) if np.any(dt > 0) else 1.0
    dt[dt <= 0] = median_dt
else:
    dt = np.ones(len(df))

# --- Reconstruct the track ---
if not df['ground_speed_mps'].isnull().all() and not df['track_deg'].isnull().all():
    lat0 = df['latitude'].iloc[0]
    lon0 = df['longitude'].iloc[0]
    rec_lat, rec_lon = reconstruct_track(lat0, lon0, df['ground_speed_mps'].values, df['track_deg'].values, dt)
else:
    rec_lat = np.full(len(df), np.nan)
    rec_lon = np.full(len(df), np.nan)

# --- Plot 1: GPS track with airspeed heatmap (current one) ---
fig1, ax1 = plt.subplots(figsize=(16, 16), dpi=300)

# Plot the raw GPS data as a thin line
ax1.plot(
    df['longitude'], df['latitude'], '-', color='red', linewidth=1, alpha=0.7,
    label='Raw GPS', path_effects=[pe.Stroke(linewidth=2, foreground='white'), pe.Normal()]
)

# Plot the smoothed route as a heatmap line based on airspeed
points = np.array([df['lon_smooth'], df['lat_smooth']]).T.reshape(-1, 1, 2)
segments = np.concatenate([points[:-1], points[1:]], axis=1)

airspeed_for_color = df['airspeed'].rolling(window=15, min_periods=1).mean().values
airspeed_for_color = (airspeed_for_color[:-1] + airspeed_for_color[1:]) / 2

norm = Normalize(vmin=np.nanmin(airspeed_for_color), vmax=np.nanmax(airspeed_for_color))
cmap = plt.get_cmap('viridis')

lc = LineCollection(
    segments, cmap=cmap, norm=norm, linewidth=2.5, alpha=1.0,
    path_effects=[pe.Stroke(linewidth=3.5, foreground='white'), pe.Normal()]
)
lc.set_array(airspeed_for_color)
line = ax1.add_collection(lc)

# Add colorbar for airspeed
cbar = plt.colorbar(line, ax=ax1, orientation='vertical', pad=0.01)
cbar.set_label('Airspeed (m/s)')

# Set plot limits and map
track_min_lon = df['lon_smooth'].min()
track_max_lon = df['lon_smooth'].max()
track_min_lat = df['lat_smooth'].min()
track_max_lat = df['lat_smooth'].max()
mean_lat = df['lat_smooth'].mean()
lat_pad = 2 / 69.0
lon_pad = 2 / (69.0 * np.cos(np.radians(mean_lat)))
min_lon, max_lon = track_min_lon - lon_pad, track_max_lon + lon_pad
min_lat, max_lat = track_min_lat - lat_pad, track_max_lat + lat_pad
map_opacity = 0.4

ax1.set_xlim(min_lon, max_lon)
ax1.set_ylim(min_lat, max_lat)
ax1.set_facecolor('black')
fig1.patch.set_facecolor('black')
ctx.add_basemap(
    ax1,
    crs='EPSG:4326',
    source=ctx.providers.OpenStreetMap.Mapnik,
    attribution_size=8,
    zoom=14,
    alpha=map_opacity
)
ax1.set_title('GPS Track with Airspeed Heatmap', fontsize=14, color='white')
ax1.legend(loc='upper right', frameon=True, framealpha=0.9, facecolor='black', edgecolor='white', labelcolor='white')
ax1.set_xlabel('')
ax1.set_ylabel('')
ax1.tick_params(colors='white')
for spine in ax1.spines.values():
    spine.set_color('white')
plt.tight_layout()
plt.savefig('gps_track_map.png', dpi=300, bbox_inches='tight', facecolor=fig1.get_facecolor())

# --- Plot 2: GPS track only ---
fig2, ax2 = plt.subplots(figsize=(16, 16), dpi=300)
ax2.plot(
    df['longitude'], df['latitude'], '-', color='cyan', linewidth=2, alpha=0.9,
    label='Raw GPS', path_effects=[pe.Stroke(linewidth=3, foreground='white'), pe.Normal()]
)
ax2.set_xlim(min_lon, max_lon)
ax2.set_ylim(min_lat, max_lat)
ax2.set_facecolor('black')
fig2.patch.set_facecolor('black')
ctx.add_basemap(
    ax2,
    crs='EPSG:4326',
    source=ctx.providers.OpenStreetMap.Mapnik,
    attribution_size=8,
    zoom=14,
    alpha=map_opacity
)
ax2.set_title('GPS Track Only', fontsize=14, color='white')
ax2.legend(loc='upper right', frameon=True, framealpha=0.9, facecolor='black', edgecolor='white', labelcolor='white')
ax2.set_xlabel('')
ax2.set_ylabel('')
ax2.tick_params(colors='white')
for spine in ax2.spines.values():
    spine.set_color('white')
plt.tight_layout()
plt.savefig('gps_track_only.png', dpi=300, bbox_inches='tight', facecolor=fig2.get_facecolor())

# --- Plot 3: Reconstructed track from ground speed and heading ---
fig3, ax3 = plt.subplots(figsize=(16, 16), dpi=300)
if not np.all(np.isnan(rec_lon)) and not np.all(np.isnan(rec_lat)):
    ax3.plot(
        rec_lon, rec_lat, '-', color='orange', linewidth=2, alpha=0.9,
        label='Reconstructed Track', path_effects=[pe.Stroke(linewidth=3, foreground='white'), pe.Normal()]
    )
    # Also plot the original GPS for comparison
    ax3.plot(
        df['longitude'], df['latitude'], '--', color='cyan', linewidth=1, alpha=0.5,
        label='Raw GPS'
    )
else:
    ax3.text(0.5, 0.5, "No reconstructed track available", color='white', ha='center', va='center', fontsize=20)
ax3.set_xlim(min_lon, max_lon)
ax3.set_ylim(min_lat, max_lat)
ax3.set_facecolor('black')
fig3.patch.set_facecolor('black')
ctx.add_basemap(
    ax3,
    crs='EPSG:4326',
    source=ctx.providers.OpenStreetMap.Mapnik,
    attribution_size=8,
    zoom=14,
    alpha=map_opacity
)
ax3.set_title('Track Reconstructed from Ground Speed and Heading', fontsize=14, color='white')
ax3.legend(loc='upper right', frameon=True, framealpha=0.9, facecolor='black', edgecolor='white', labelcolor='white')
ax3.set_xlabel('')
ax3.set_ylabel('')
ax3.tick_params(colors='white')
for spine in ax3.spines.values():
    spine.set_color('white')
plt.tight_layout()
plt.savefig('reconstructed_track_map.png', dpi=300, bbox_inches='tight', facecolor=fig3.get_facecolor())

# --- Plot 4: Ground speed and airspeed over time (smoothed), their difference, and heading ---
# Compute rolling means
airspeed_rolling = df['airspeed'].rolling(window=15, min_periods=1).mean()
ground_speed_rolling = df['ground_speed_mps'].rolling(window=15, min_periods=1).mean()
diff_rolling = airspeed_rolling - ground_speed_rolling

# For heading, wrap to [0, 360) and interpolate for smoothness
heading = df['track_deg']
heading_wrapped = (heading % 360).copy()
# Optionally interpolate NaNs for heading for plotting
heading_wrapped_interp = heading_wrapped.interpolate(limit_direction='both')

# Use time as x-axis if available, else index
if 'time' in df.columns:
    time_x = df['time']
else:
    time_x = np.arange(len(df))

fig4, ax4 = plt.subplots(figsize=(14, 7), dpi=200)
ax4.plot(time_x, airspeed_rolling, label='Airspeed (15pt avg)', color='blue')
ax4.plot(time_x, ground_speed_rolling, label='Ground Speed (15pt avg)', color='green')
ax4.plot(time_x, diff_rolling, label='Airspeed - Ground Speed', color='red', linestyle='--')
ax4.set_title('Airspeed, Ground Speed, and Heading (15-point Rolling Average)', fontsize=14)
ax4.set_xlabel('Time' if 'time' in df.columns else 'Index')
ax4.set_ylabel('Speed (m/s)')
ax4.legend(loc='upper left')
ax4.grid(True, alpha=0.3)

# Add heading on right y-axis
ax4b = ax4.twinx()
ax4b.plot(time_x, heading_wrapped_interp, color='purple', label='Heading (deg)', linewidth=1.5, alpha=0.7)
ax4b.set_ylabel('Heading (deg)')
ax4b.set_ylim(0, 360)
ax4b.set_yticks(np.arange(0, 361, 60))
ax4b.set_yticklabels([str(int(x)) for x in np.arange(0, 361, 60)])
ax4b.spines['right'].set_color('purple')
ax4b.tick_params(axis='y', colors='purple')

# Add heading legend
lines, labels = ax4.get_legend_handles_labels()
lines2, labels2 = ax4b.get_legend_handles_labels()
ax4b.legend(lines + lines2, labels + labels2, loc='upper right')

plt.tight_layout()
plt.savefig('airspeed_groundspeed_time.png', dpi=200)
