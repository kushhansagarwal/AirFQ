import os
import uuid
import boto3
from datetime import datetime
import tempfile
import logging

# Set MPLCONFIGDIR to a writable temp directory before importing matplotlib
import tempfile
mplconfigdir = os.environ.get("MPLCONFIGDIR")
if not mplconfigdir:
    temp_mpl_dir = tempfile.mkdtemp(prefix="mplconfigdir_")
    os.environ["MPLCONFIGDIR"] = temp_mpl_dir

import requests
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.basemap import Basemap
from datetime import datetime, timezone, timedelta
from math import radians, sin, cos, sqrt, atan2

padding = 0.1

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

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
    if response.status_code == requests.codes.ok:
        data = response.json()
        if data:
            return data[0]
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
        return None, None, None

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

# --- Helper for consistent plot sizing and aspect ratio ---
def get_plot_dimensions(min_lon, max_lon, min_lat, max_lat, base_dpi=300, base_width=15, max_pixels=2000):
    """
    Returns (figsize, dpi) for a given bounding box, keeping a fixed width and aspect ratio.
    Limits the maximum dimension to max_pixels.
    """
    # Calculate aspect ratio (width:height) based on degrees
    width_deg = max_lon - min_lon
    height_deg = max_lat - min_lat
    if height_deg == 0:
        height_deg = 1e-6  # avoid division by zero
    aspect = width_deg / height_deg
    
    # Keep width fixed, adjust height for aspect
    width = base_width
    height = width / aspect
    
    # Optionally, clamp height to a reasonable range
    height = max(5, min(height, 30))
    
    # Calculate actual pixel dimensions
    width_px = width * base_dpi
    height_px = height * base_dpi
    
    # If either dimension exceeds max_pixels, scale down
    if width_px > max_pixels or height_px > max_pixels:
        if width_px > height_px:
            scale_factor = max_pixels / width_px
        else:
            scale_factor = max_pixels / height_px
        
        # Either reduce the figure size or the DPI to achieve the target size
        # Here we're adjusting the DPI
        adjusted_dpi = base_dpi * scale_factor
        return (width, height), adjusted_dpi
    
    return (width, height), base_dpi

def plot_wind_data(
    data, airport_coords, airport_names, level, output_dir,
    plot_bbox=None, plot_figsize=None, plot_dpi=None, max_pixels=2000
):
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
    if plot_bbox is not None:
        min_lon, max_lon, min_lat, max_lat = plot_bbox
    else:
        min_lon = min(from_lon, to_lon) - padding
        max_lon = max(from_lon, to_lon) + padding
        min_lat = min(from_lat, to_lat) - padding
        max_lat = max(from_lat, to_lat) + padding

    # Get consistent figure size and dpi
    if plot_figsize is None or plot_dpi is None:
        plot_figsize, plot_dpi = get_plot_dimensions(min_lon, max_lon, min_lat, max_lat, max_pixels=max_pixels)

    try:
        lon_grid, lat_grid, elevation = fetch_terrain_data(min_lon, max_lon, min_lat, max_lat)
    except Exception:
        lon_grid, lat_grid, elevation = None, None, None

    plt.rcParams['svg.fonttype'] = 'none'
    fig = plt.figure(figsize=plot_figsize, dpi=plot_dpi)
    ax = fig.add_axes([0, 0, 1, 1])  # full-figure axes, no border

    # Set white background
    fig.patch.set_facecolor('white')
    ax.set_facecolor('white')

    m = Basemap(projection='merc', llcrnrlat=min_lat, urcrnrlat=max_lat,
                llcrnrlon=min_lon, urcrnrlon=max_lon, resolution='i', ax=ax)

    if lon_grid is not None and lat_grid is not None and elevation is not None:
        elev_masked = np.ma.masked_invalid(elevation)
        x_terr, y_terr = m(lon_grid, lat_grid)
        vmin = np.nanmin(elev_masked)
        vmax = np.nanmax(elev_masked)
        vmin = max(0, vmin)
        vmax = max(vmax, vmin + 1)
        m.pcolormesh(x_terr, y_terr, elev_masked, cmap='terrain', shading='auto', alpha=0.6, vmin=vmin, vmax=vmax)

    m.drawcoastlines(linewidth=0.5)
    m.drawcountries(linewidth=0.5)
    m.drawstates(linewidth=0.3)
    m.drawparallels(np.arange(int(min_lat), int(max_lat) + 1, 2), labels=[0, 0, 0, 0])
    m.drawmeridians(np.arange(int(min_lon), int(max_lon) + 1, 2), labels=[0, 0, 0, 0])

    x, y = m(lons, lats)
    m.quiver(x, y, u_components, v_components, color='blue', scale=500, width=0.003)

    x_from, y_from = m(from_lon, from_lat)
    x_to, y_to = m(to_lon, to_lat)
    m.plot(x_from, y_from, 'ro', markersize=10)
    m.plot(x_to, y_to, 'go', markersize=10)
    m.plot([x_from, x_to], [y_from, y_to], 'k-', linewidth=2)

    # Remove all axes, ticks, spines, and title
    ax.set_axis_off()
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
    # fig.patch.set_visible(False)  # keep white background

    output_file = os.path.join(output_dir, f'wind_data_{airport_names[0]}_to_{airport_names[1]}_FL{level}.png')
    plt.savefig(output_file, format='png', bbox_inches='tight', pad_inches=0.0, transparent=False, facecolor='white', dpi=600)
    plt.close(fig)
    return output_file

def plot_wind_data_augmented(
    data, airport_coords, airport_names, level, output_dir, magnitude_factor, angle_factor,
    plot_bbox=None, plot_figsize=None, plot_dpi=None, max_pixels=2000
):
    features = data['features']
    lons = []
    lats = []
    u_components = []
    v_components = []
    u_components_augmented = []
    v_components_augmented = []
    augmentation_texts = []
    augmentation_coords = []

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
                wspd_augmented = wspd * magnitude_factor
                angle_augmentation = wspd * angle_factor
                wdir_augmented = wdir + angle_augmentation
                rad_augmented = np.deg2rad(wdir_augmented)
                u_augmented = wspd_augmented * np.sin(rad_augmented)
                v_augmented = wspd_augmented * np.cos(rad_augmented)
                u_components_augmented.append(u_augmented)
                v_components_augmented.append(v_augmented)
                heading_diff = wdir_augmented - wdir
                wspd_diff = wspd_augmented - wspd
                diff_text = f"{heading_diff:+.1f}° / {wspd_diff:+.1f}kt"
                augmentation_texts.append(diff_text)
                augmentation_coords.append((lon, lat))

    from_lon, from_lat = airport_coords[0]
    to_lon, to_lat = airport_coords[1]
    if plot_bbox is not None:
        min_lon, max_lon, min_lat, max_lat = plot_bbox
    else:
        min_lon = min(from_lon, to_lon) - padding
        max_lon = max(from_lon, to_lon) + padding
        min_lat = min(from_lat, to_lat) - padding
        max_lat = max(from_lat, to_lat) + padding

    # Get consistent figure size and dpi
    if plot_figsize is None or plot_dpi is None:
        plot_figsize, plot_dpi = get_plot_dimensions(min_lon, max_lon, min_lat, max_lat, max_pixels=max_pixels)

    try:
        lon_grid, lat_grid, elevation = fetch_terrain_data(min_lon, max_lon, min_lat, max_lat)
    except Exception:
        lon_grid, lat_grid, elevation = None, None, None

    plt.rcParams['svg.fonttype'] = 'none'
    fig = plt.figure(figsize=plot_figsize, dpi=plot_dpi)
    ax = fig.add_axes([0, 0, 1, 1])  # full-figure axes, no border

    # Set white background
    fig.patch.set_facecolor('white')
    ax.set_facecolor('white')

    m = Basemap(projection='merc', llcrnrlat=min_lat, urcrnrlat=max_lat,
                llcrnrlon=min_lon, urcrnrlon=max_lon, resolution='i', ax=ax)

    if lon_grid is not None and lat_grid is not None and elevation is not None:
        elev_masked = np.ma.masked_invalid(elevation)
        x_terr, y_terr = m(lon_grid, lat_grid)
        vmin = np.nanmin(elev_masked)
        vmax = np.nanmax(elev_masked)
        vmin = max(0, vmin)
        vmax = max(vmax, vmin + 1)
        m.pcolormesh(x_terr, y_terr, elev_masked, cmap='terrain', shading='auto', alpha=0.6, vmin=vmin, vmax=vmax)

    m.drawcoastlines(linewidth=0.5)
    m.drawcountries(linewidth=0.5)
    m.drawstates(linewidth=0.3)
    m.drawparallels(np.arange(int(min_lat), int(max_lat) + 1, 2), labels=[0, 0, 0, 0])
    m.drawmeridians(np.arange(int(min_lon), int(max_lon) + 1, 2), labels=[0, 0, 0, 0])

    x, y = m(lons, lats)
    m.quiver(x, y, u_components, v_components, color='blue', scale=500, width=0.003, alpha=0.4)
    m.quiver(x, y, u_components_augmented, v_components_augmented, color='red', scale=500, width=0.003, alpha=0.8)

    # for (lon, lat), diff_text in zip(augmentation_coords, augmentation_texts):
    #     x_pt, y_pt = m(lon, lat)
    #     plt.text(
    #         x_pt + 2000, y_pt + 2000,
    #         diff_text,
    #         fontsize=7, color='purple', alpha=0.85,
    #         ha='left', va='bottom',
    #         zorder=11,
    #         bbox=dict(facecolor='white', edgecolor='none', alpha=0.5, boxstyle='round,pad=0.1')
    #     )

    x_from, y_from = m(from_lon, from_lat)
    x_to, y_to = m(to_lon, to_lat)
    m.plot(x_from, y_from, 'ro', markersize=10)
    m.plot(x_to, y_to, 'go', markersize=10)
    m.plot([x_from, x_to], [y_from, y_to], 'k-', linewidth=2)

    # Remove all axes, ticks, spines, and title
    ax.set_axis_off()
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
    # fig.patch.set_visible(False)  # keep white background

    output_file = os.path.join(output_dir, 
                              f'wind_data_augmented_{airport_names[0]}_to_{airport_names[1]}_FL{level}.png')
    plt.savefig(output_file, format='png', bbox_inches='tight', pad_inches=0.0, transparent=False, facecolor='white', dpi=600)
    plt.close(fig)
    return output_file

def generate_wind_plots(departure_icao, arrival_icao, levels, output_dir, max_pixels=2000):
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

    # Get consistent plot size/aspect for this airport pair
    plot_bbox = (min_lon, max_lon, min_lat, max_lat)
    plot_figsize, plot_dpi = get_plot_dimensions(min_lon, max_lon, min_lat, max_lat, max_pixels=max_pixels)

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
        plot_file = plot_wind_data(
            response_data, airport_coords, airport_names, level, output_dir,
            plot_bbox=plot_bbox, plot_figsize=plot_figsize, plot_dpi=plot_dpi, max_pixels=max_pixels
        )
        plot_files.append(plot_file)
    return plot_files

def generate_wind_plots_augmented(departure_icao, arrival_icao, levels, output_dir, magnitude_factor, angle_factor, max_pixels=2000):
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

    # Get consistent plot size/aspect for this airport pair
    plot_bbox = (min_lon, max_lon, min_lat, max_lat)
    plot_figsize, plot_dpi = get_plot_dimensions(min_lon, max_lon, min_lat, max_lat, max_pixels=max_pixels)

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
        plot_file = plot_wind_data_augmented(
            response_data, airport_coords, airport_names, 
            level, output_dir, magnitude_factor, angle_factor,
            plot_bbox=plot_bbox, plot_figsize=plot_figsize, plot_dpi=plot_dpi, max_pixels=max_pixels
        )
        plot_files.append(plot_file)
    return plot_files

def get_s3_client():
    return boto3.client(
        's3',
        aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
        region_name=os.environ.get('AWS_REGION', 'us-west-2')
    )

S3_BUCKET = os.environ.get('S3_BUCKET', 'airfq')
S3_REGION = os.environ.get('AWS_REGION', 'us-west-2')

# --- S3 upload helper ---
def upload_file_to_s3(file_path, bucket=S3_BUCKET, region=S3_REGION, object_name=None):
    s3 = get_s3_client()
    if object_name is None:
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        random_id = str(uuid.uuid4())[:8]
        object_name = f"wind-plots/{timestamp}-{random_id}-{os.path.basename(file_path)}"
    try:
        s3.upload_file(
            file_path, bucket, object_name,
            ExtraArgs={
                'ContentType': 'image/png',
                'ContentDisposition': 'inline'
            }
        )
        url = f"https://{bucket}.s3.{region}.amazonaws.com/{object_name}"
        return url
    except Exception as e:
        logging.error(f"Error uploading to S3: {str(e)}")
        raise

# --- Main API helpers ---
def generate_and_upload_wind_plot(
    departure, arrival, level, magnitude_factor=None, angle_factor=None, low_res=True, augmented=False
):
    """
    Generate a wind plot, upload to S3, delete temp file, and return the S3 URL.
    """
    max_pixels = 600 if low_res else 2000
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            if augmented:
                if magnitude_factor is None:
                    magnitude_factor = 1.5
                if angle_factor is None:
                    angle_factor = 0.5
                plot_files = generate_wind_plots_augmented(
                    departure, arrival, [level], temp_dir, magnitude_factor, angle_factor, max_pixels=max_pixels
                )
            else:
                plot_files = generate_wind_plots(
                    departure, arrival, [level], temp_dir, max_pixels=max_pixels
                )
            if not plot_files or not os.path.exists(plot_files[0]):
                raise RuntimeError('Failed to generate wind plot')
            plot_file = plot_files[0]
            s3_url = upload_file_to_s3(plot_file)
            # Delete the file explicitly (though temp_dir will be cleaned up)
            try:
                os.remove(plot_file)
            except Exception:
                pass
            return s3_url
        except Exception as e:
            logging.error(f"Error in generate_and_upload_wind_plot: {e}")
            raise

if __name__ == '__main__':
    departure = "KSMO"
    arrival = "KSBA"
    levels = ['030', '050', '070', '090', '120']
    output_dir = "."
    try:
        plot_files = generate_wind_plots(departure, arrival, levels, output_dir)
        print(f"Generated {len(plot_files)} wind data plots:")
    except Exception as e:
        print(f"Error generating wind data plots: {e}")
