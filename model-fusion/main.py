import os

# Set MPLCONFIGDIR to a writable temp directory before importing matplotlib
import tempfile
mplconfigdir = os.environ.get("MPLCONFIGDIR")
if not mplconfigdir:
    temp_mpl_dir = tempfile.mkdtemp(prefix="mplconfigdir_")
    os.environ["MPLCONFIGDIR"] = temp_mpl_dir

import requests
import matplotlib
# Use Agg backend to avoid GUI issues when running in a non-main thread
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.basemap import Basemap
from datetime import datetime, timezone, timedelta
import threading
from math import radians, sin, cos, sqrt, atan2

padding = 0.1

def haversine(lat1, lon1, lat2, lon2):
    # Radius of the Earth in km
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

 # Define a function to map distance to zoom level
def get_zoom_for_distance(distance_km):
    if distance_km < 100:
        return "12"
    elif distance_km < 250:
        return "11"
    elif distance_km < 500:
        return "10"
    elif distance_km < 1000:
        return "9"
    elif distance_km < 2000:
        return "8"
    else:
        return "7"

def get_airport_by_icao(icao_code):
    api_url = f'https://api.api-ninjas.com/v1/airports?icao={icao_code}'
    response = requests.get(api_url, headers={'X-Api-Key': os.getenv('AIRPORT_KEY')})
    print(f"Requesting airport info: {response.url}")
    if response.status_code == requests.codes.ok:
        data = response.json()
        if data:
            return data[0]  # API returns a list of airports
    return None

def make_request_with_params(base_url, params):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    response = requests.get(base_url, params=params, headers=headers)
    return response.json()

def fetch_terrain_data(min_lon, max_lon, min_lat, max_lat, resolution=0.05):
    url = "https://portal.opentopography.org/API/globaldem"
    params = {
        "demtype": "SRTMGL1",
        "south": min_lat,
        "north": max_lat,
        "west": min_lon,
        "east": max_lon,
        "outputFormat": "AAIGrid"
    }
    response = requests.get(url, params=params)
    if response.status_code != 200:
        print(f"Failed to fetch terrain data: {response.status_code}")
        return None, None, None

    from io import StringIO
    content = response.text
    header_lines = []
    data_lines = []
    for line in content.splitlines():
        if line.strip() == "":
            continue
        if len(header_lines) < 6:
            header_lines.append(line)
        else:
            data_lines.append(line)
    header = {}
    for line in header_lines:
        k, v = line.strip().split()
        header[k.lower()] = float(v)
    ncols = int(header['ncols'])
    nrows = int(header['nrows'])
    xllcorner = header['xllcorner']
    yllcorner = header['yllcorner']
    cellsize = header['cellsize']
    nodata = header['nodata_value']

    data = []
    for line in data_lines:
        data.extend([float(x) for x in line.strip().split()])
    elevation = np.array(data).reshape((nrows, ncols))
    elevation[elevation == nodata] = np.nan

    lons = xllcorner + np.arange(ncols) * cellsize
    lats = yllcorner + np.arange(nrows) * cellsize
    lats = lats[::-1]
    elevation = np.flipud(elevation)
    lon_grid, lat_grid = np.meshgrid(lons, lats)
    return lon_grid, lat_grid, elevation

def plot_wind_data(data, airport_coords, airport_names, level, output_dir):
    features = data['features']
    lons = []
    lats = []
    u_components = []
    v_components = []

    for feature in features:
        if 'geometry' in feature and 'coordinates' in feature['geometry']:
            lon, lat = feature['geometry']['coordinates']
            if 'properties' in feature and 'wdir' in feature['properties'] and 'wspd' in feature['properties']:
                wdir = feature['properties']['wdir']
                wspd = feature['properties']['wspd']

                try:
                    wdir = float(wdir)
                    wspd = float(wspd)
                except ValueError:
                    continue

                lons.append(lon)
                lats.append(lat)

                rad = np.deg2rad(wdir)
                u = wspd * np.sin(rad)
                v = wspd * np.cos(rad)
                u_components.append(u)
                v_components.append(v)

    from_lon, from_lat = airport_coords[0]
    to_lon, to_lat = airport_coords[1]
    
    min_lon = min(from_lon, to_lon) - padding
    max_lon = max(from_lon, to_lon) + padding
    min_lat = min(from_lat, to_lat) - padding
    max_lat = max(from_lat, to_lat) + padding

    try:
        lon_grid, lat_grid, elevation = fetch_terrain_data(min_lon, max_lon, min_lat, max_lat)
    except Exception as terr_e:
        print(f"Error fetching terrain data: {terr_e}")
        lon_grid, lat_grid, elevation = None, None, None

    plt.rcParams['svg.fonttype'] = 'none'
    fig = plt.figure(figsize=(15, 10), dpi=300)

    m = Basemap(projection='merc', llcrnrlat=min_lat, urcrnrlat=max_lat,
                llcrnrlon=min_lon, urcrnrlon=max_lon, resolution='i')

    if lon_grid is not None and lat_grid is not None and elevation is not None:
        elev_masked = np.ma.masked_invalid(elevation)
        x_terr, y_terr = m(lon_grid, lat_grid)
        vmin = np.nanmin(elev_masked)
        vmax = np.nanmax(elev_masked)
        vmin = max(0, vmin)
        vmax = max(vmax, vmin + 1)
        m.pcolormesh(x_terr, y_terr, elev_masked, cmap='terrain', shading='auto', alpha=0.6, vmin=vmin, vmax=vmax)
        cbar = plt.colorbar(label='Elevation (m)', shrink=0.7, pad=0.02)
        cbar.ax.tick_params(labelsize=10)

    m.drawcoastlines(linewidth=0.5)
    m.drawcountries(linewidth=0.5)
    m.drawstates(linewidth=0.3)
    
    m.drawparallels(np.arange(int(min_lat), int(max_lat) + 1, 2), labels=[1, 0, 0, 0])
    m.drawmeridians(np.arange(int(min_lon), int(max_lon) + 1, 2), labels=[0, 0, 0, 1])

    x, y = m(lons, lats)
    m.quiver(x, y, u_components, v_components, 
             color='blue', scale=500, width=0.003)

    x_from, y_from = m(from_lon, from_lat)
    x_to, y_to = m(to_lon, to_lat)
    
    m.plot(x_from, y_from, 'ro', markersize=10)
    plt.text(x_from, y_from, airport_names[0], fontsize=12, color='black',
             horizontalalignment='right', verticalalignment='bottom')
    
    m.plot(x_to, y_to, 'go', markersize=10)
    plt.text(x_to, y_to, airport_names[1], fontsize=12, color='black',
             horizontalalignment='right', verticalalignment='bottom')
    
    m.plot([x_from, x_to], [y_from, y_to], 'k-', linewidth=2)

    plt.title(f'Wind Data for Route: {airport_names[0]} to {airport_names[1]} (FL{level})')
    plt.grid(True, alpha=0.3)
    
    output_file = os.path.join(output_dir, f'wind_data_{airport_names[0]}_to_{airport_names[1]}_FL{level}.svg')
    plt.savefig(output_file, format='svg', bbox_inches='tight', pad_inches=0.1)
    plt.close(fig)
    
    return output_file

def plot_wind_data_augmented(data, airport_coords, airport_names, level, output_dir, magnitude_factor, angle_factor):
    features = data['features']
    lons = []
    lats = []
    u_components = []
    v_components = []
    u_components_augmented = []
    v_components_augmented = []
    augmentation_texts = []
    augmentation_coords = []

    # We'll store the augmentation info for each point to plot after the map is set up
    for feature in features:
        if 'geometry' in feature and 'coordinates' in feature['geometry']:
            lon, lat = feature['geometry']['coordinates']
            if 'properties' in feature and 'wdir' in feature['properties'] and 'wspd' in feature['properties']:
                wdir = feature['properties']['wdir']
                wspd = feature['properties']['wspd']

                try:
                    wdir = float(wdir)
                    wspd = float(wspd)
                except ValueError:
                    continue

                lons.append(lon)
                lats.append(lat)

                # Original wind components
                rad = np.deg2rad(wdir)
                u = wspd * np.sin(rad)
                v = wspd * np.cos(rad)
                u_components.append(u)
                v_components.append(v)

                # Augmented wind components
                wspd_augmented = wspd * magnitude_factor
                angle_augmentation = wspd * angle_factor  # Proportional to wind speed
                wdir_augmented = wdir + angle_augmentation
                rad_augmented = np.deg2rad(wdir_augmented)
                u_augmented = wspd_augmented * np.sin(rad_augmented)
                v_augmented = wspd_augmented * np.cos(rad_augmented)
                u_components_augmented.append(u_augmented)
                v_components_augmented.append(v_augmented)

                # Compute difference in heading and windspeed
                heading_diff = wdir_augmented - wdir
                wspd_diff = wspd_augmented - wspd
                # Format as +X.X° / +Y.Y kt (or -)
                diff_text = f"{heading_diff:+.1f}° / {wspd_diff:+.1f}kt"
                # Save for later plotting
                augmentation_texts.append(diff_text)
                augmentation_coords.append((lon, lat))

    from_lon, from_lat = airport_coords[0]
    to_lon, to_lat = airport_coords[1]
    
    min_lon = min(from_lon, to_lon) - padding
    max_lon = max(from_lon, to_lon) + padding
    min_lat = min(from_lat, to_lat) - padding
    max_lat = max(from_lat, to_lat) + padding

    try:
        lon_grid, lat_grid, elevation = fetch_terrain_data(min_lon, max_lon, min_lat, max_lat)
    except Exception as terr_e:
        print(f"Error fetching terrain data: {terr_e}")
        lon_grid, lat_grid, elevation = None, None, None

    plt.rcParams['svg.fonttype'] = 'none'
    fig = plt.figure(figsize=(15, 10), dpi=300)

    m = Basemap(projection='merc', llcrnrlat=min_lat, urcrnrlat=max_lat,
                llcrnrlon=min_lon, urcrnrlon=max_lon, resolution='i')

    if lon_grid is not None and lat_grid is not None and elevation is not None:
        elev_masked = np.ma.masked_invalid(elevation)
        x_terr, y_terr = m(lon_grid, lat_grid)
        vmin = np.nanmin(elev_masked)
        vmax = np.nanmax(elev_masked)
        vmin = max(0, vmin)
        vmax = max(vmax, vmin + 1)
        m.pcolormesh(x_terr, y_terr, elev_masked, cmap='terrain', shading='auto', alpha=0.6, vmin=vmin, vmax=vmax)
        cbar = plt.colorbar(label='Elevation (m)', shrink=0.7, pad=0.02)
        cbar.ax.tick_params(labelsize=10)

    m.drawcoastlines(linewidth=0.5)
    m.drawcountries(linewidth=0.5)
    m.drawstates(linewidth=0.3)
    
    m.drawparallels(np.arange(int(min_lat), int(max_lat) + 1, 2), labels=[1, 0, 0, 0])
    m.drawmeridians(np.arange(int(min_lon), int(max_lon) + 1, 2), labels=[0, 0, 0, 1])

    x, y = m(lons, lats)
    
    # Plot original wind vectors in blue with lower opacity
    m.quiver(x, y, u_components, v_components, 
             color='blue', scale=500, width=0.003, alpha=0.4, label='Original Winds')
    
    # Plot augmented wind vectors in red
    m.quiver(x, y, u_components_augmented, v_components_augmented, 
             color='red', scale=500, width=0.003, alpha=0.8, label='Augmented Winds')

    # Plot augmentation info next to each point
    for (lon, lat), diff_text in zip(augmentation_coords, augmentation_texts):
        x_pt, y_pt = m(lon, lat)
        # Offset the text slightly so it doesn't overlap the arrow base
        plt.text(
            x_pt + 2000, y_pt + 2000,  # Offset in map coordinates (tune as needed)
            diff_text,
            fontsize=7, color='purple', alpha=0.85,
            ha='left', va='bottom',
            zorder=11,
            bbox=dict(facecolor='white', edgecolor='none', alpha=0.5, boxstyle='round,pad=0.1')
        )

    x_from, y_from = m(from_lon, from_lat)
    x_to, y_to = m(to_lon, to_lat)
    
    m.plot(x_from, y_from, 'ro', markersize=10)
    plt.text(x_from, y_from, airport_names[0], fontsize=12, color='black',
             horizontalalignment='right', verticalalignment='bottom')
    
    m.plot(x_to, y_to, 'go', markersize=10)
    plt.text(x_to, y_to, airport_names[1], fontsize=12, color='black',
             horizontalalignment='right', verticalalignment='bottom')
    
    m.plot([x_from, x_to], [y_from, y_to], 'k-', linewidth=2)

    plt.title(f'Wind Data for Route: {airport_names[0]} to {airport_names[1]} (FL{level})\n' +
              f'Magnitude Factor: {magnitude_factor:.1f}, Angle Factor: {angle_factor:.1f}°/kt')
    plt.grid(True, alpha=0.3)
    
    plt.legend(loc='upper right')
    
    output_file = os.path.join(output_dir, 
                              f'wind_data_augmented_{airport_names[0]}_to_{airport_names[1]}_FL{level}.svg')
    plt.savefig(output_file, format='svg', bbox_inches='tight', pad_inches=0.1)
    plt.close(fig)
    
    return output_file

def generate_wind_plots(departure_icao, arrival_icao, levels, output_dir):
    from_airport = get_airport_by_icao(departure_icao)
    to_airport = get_airport_by_icao(arrival_icao)

    if not from_airport:
        raise ValueError(f"Airport with ICAO code '{departure_icao}' not found.")
    if not to_airport:
        raise ValueError(f"Airport with ICAO code '{arrival_icao}' not found.")

    from_lat = float(from_airport['latitude'])
    from_lon = float(from_airport['longitude'])
    to_lat = float(to_airport['latitude'])
    to_lon = float(to_airport['longitude'])

    current_date = datetime.now().astimezone(timezone(timedelta(hours=-8))).strftime("%Y%m%d")

    min_lat = min(from_lat, to_lat) - padding
    max_lat = max(from_lat, to_lat) + padding
    min_lon = min(from_lon, to_lon) - padding
    max_lon = max(from_lon, to_lon) + padding

    base_url = "https://aviationweather.gov/api/json/ModelWindsJSON"
    plot_files = []
    
    route_distance_km = haversine(from_lat, from_lon, to_lat, to_lon)
    zoom_level = get_zoom_for_distance(route_distance_km)

    for level in levels:
        params = {
            "wrap": "true",
            "zoom": zoom_level,
            "model": "gfaak",
            "level": level,
            "density": "0",
            "bbox": f"{min_lon},{min_lat},{max_lon},{max_lat}",
            "dref": current_date,
            "tref": "00",
            "fhr": "00"
        }

        response_data = make_request_with_params(base_url, params)
        airport_coords = [(from_lon, from_lat), (to_lon, to_lat)]
        airport_names = [from_airport['icao'], to_airport['icao']]
        
        plot_file = plot_wind_data(response_data, airport_coords, airport_names, level, output_dir)
        plot_files.append(plot_file)

    return plot_files

def generate_wind_plots_augmented(departure_icao, arrival_icao, levels, output_dir, magnitude_factor, angle_factor):
    from_airport = get_airport_by_icao(departure_icao)
    to_airport = get_airport_by_icao(arrival_icao)

    if not from_airport:
        raise ValueError(f"Airport with ICAO code '{departure_icao}' not found.")
    if not to_airport:
        raise ValueError(f"Airport with ICAO code '{arrival_icao}' not found.")

    from_lat = float(from_airport['latitude'])
    from_lon = float(from_airport['longitude'])
    to_lat = float(to_airport['latitude'])
    to_lon = float(to_airport['longitude'])

    current_date = datetime.now().astimezone(timezone(timedelta(hours=-8))).strftime("%Y%m%d")

    min_lat = min(from_lat, to_lat) - padding
    max_lat = max(from_lat, to_lat) + padding
    min_lon = min(from_lon, to_lon) - padding
    max_lon = max(from_lon, to_lon) + padding

    route_distance_km = haversine(from_lat, from_lon, to_lat, to_lon)
    zoom_level = get_zoom_for_distance(route_distance_km)

    base_url = "https://aviationweather.gov/api/json/ModelWindsJSON"
    plot_files = []

    for level in levels:
        params = {
            "wrap": "true",
            "zoom": zoom_level,
            "model": "gfaak",
            "level": level,
            "density": "0",
            "bbox": f"{min_lon},{min_lat},{max_lon},{max_lat}",
            "dref": current_date,
            "tref": "00",
            "fhr": "00"
        }

        response_data = make_request_with_params(base_url, params)
        airport_coords = [(from_lon, from_lat), (to_lon, to_lat)]
        airport_names = [from_airport['icao'], to_airport['icao']]
        
        plot_file = plot_wind_data_augmented(response_data, airport_coords, airport_names, 
                                           level, output_dir, magnitude_factor, angle_factor)
        plot_files.append(plot_file)

    return plot_files

if __name__ == '__main__':
    # Example usage when running the script directly
    departure = "KSMO"
    arrival = "KSBA"
    levels = ['030', '050', '070', '090', '120']
    output_dir = "."
    
    try:
        plot_files = generate_wind_plots(departure, arrival, levels, output_dir)
        print(f"Generated {len(plot_files)} wind data plots:")
    except Exception as e:
        print(f"Error generating wind data plots: {e}")
