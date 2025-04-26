import requests
import os
import matplotlib
# Use Agg backend to avoid GUI issues when running in a non-main thread
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.basemap import Basemap
from datetime import datetime, timezone, timedelta
import threading

padding = 1

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
    """
    Fetch SRTM elevation data from OpenTopography API for the given bounding box.
    Returns: lon_grid, lat_grid, elevation_grid (all as 2D numpy arrays)
    """
    # OpenTopography SRTM API endpoint
    # See: https://portal.opentopography.org/apidocs/#/Public/getGlobalDem
    url = "https://portal.opentopography.org/API/globaldem"
    params = {
        "demtype": "SRTMGL1",  # 30m SRTM
        "south": min_lat,
        "north": max_lat,
        "west": min_lon,
        "east": max_lon,
        "outputFormat": "AAIGrid"
    }
    # The API is public, but may require registration for high volume
    response = requests.get(url, params=params)
    if response.status_code != 200:
        print(f"Failed to fetch terrain data: {response.status_code}")
        return None, None, None

    # Parse ASCII Grid (AAIGrid) format
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
    # Parse header
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

    # Parse data
    data = []
    for line in data_lines:
        data.extend([float(x) for x in line.strip().split()])
    elevation = np.array(data).reshape((nrows, ncols))
    # Replace nodata with nan
    elevation[elevation == nodata] = np.nan

    # Build coordinate grids
    lons = xllcorner + np.arange(ncols) * cellsize
    lats = yllcorner + np.arange(nrows) * cellsize
    # The grid is from top (north) to bottom (south), so flip lats and elevation
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

    # Fetch terrain data for the bounding box
    try:
        lon_grid, lat_grid, elevation = fetch_terrain_data(min_lon, max_lon, min_lat, max_lat)
    except Exception as terr_e:
        print(f"Error fetching terrain data: {terr_e}")
        lon_grid, lat_grid, elevation = None, None, None

    # Create figure with high DPI for better SVG quality
    plt.rcParams['svg.fonttype'] = 'none'  # Ensure text remains as text in SVG
    fig = plt.figure(figsize=(15, 10), dpi=300)

    m = Basemap(projection='merc', llcrnrlat=min_lat, urcrnrlat=max_lat,
                llcrnrlon=min_lon, urcrnrlon=max_lon, resolution='i')

    # Draw terrain as a colored background
    if lon_grid is not None and lat_grid is not None and elevation is not None:
        # Mask nan values for plotting
        elev_masked = np.ma.masked_invalid(elevation)
        # Project grid to map coordinates
        x_terr, y_terr = m(lon_grid, lat_grid)
        # Use a colormap suitable for elevation
        # Use a light alpha so wind vectors and lines are visible
        # Use terrain colormap, but clip to reasonable elevation range
        vmin = np.nanmin(elev_masked)
        vmax = np.nanmax(elev_masked)
        # Avoid negative vmin for color scaling
        vmin = max(0, vmin)
        vmax = max(vmax, vmin + 1)
        m.pcolormesh(x_terr, y_terr, elev_masked, cmap='terrain', shading='auto', alpha=0.6, vmin=vmin, vmax=vmax)
        # Add a colorbar for terrain
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
    plt.grid(True, alpha=0.3)  # Make grid lighter for better SVG appearance
    
    output_file = os.path.join(output_dir, f'wind_data_{airport_names[0]}_to_{airport_names[1]}_FL{level}.svg')
    plt.savefig(output_file, format='svg', bbox_inches='tight', pad_inches=0.1)
    plt.close(fig)
    
    return output_file

def generate_wind_plots(departure_icao, arrival_icao, levels, output_dir):
    """
    Generate wind plots for multiple flight levels between two airports.
    
    Args:
        departure_icao (str): ICAO code of departure airport
        arrival_icao (str): ICAO code of arrival airport
        levels (list): List of flight levels to generate plots for
        output_dir (str): Directory to save the plots
        
    Returns:
        list: List of paths to generated plot files
    """
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

    for level in levels:
        params = {
            "wrap": "true",
            "zoom": "10",

            "model": "gfaak",  # Changed from gfaak to gfs for better data availability
            "level": level,
            "density": "0",  # Increased density for better data resolution
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
