#!/usr/bin/env python

from flask import Flask, request, jsonify, send_file, make_response
import os
from main import generate_wind_plots, generate_wind_plots_augmented
import tempfile
from werkzeug.utils import secure_filename
from websockets.sync.client import connect
import json

app = Flask(__name__)

@app.after_request
def after_request(response):
    # Allow CORS from anywhere
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
    return response

@app.route('/wind-data', methods=['POST'])
def get_wind_data():
    # Accept both JSON and form data for flexibility
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form.to_dict()

    # Validate input
    if not data or 'departure' not in data or 'arrival' not in data or 'level' not in data:
        return jsonify({'error': 'Missing required parameters (departure, arrival, level)'}), 400
        
    departure = data['departure']
    arrival = data['arrival']
    level = data['level']

    # Accept level as a string, or as an int (convert to string with leading zeros)
    if isinstance(level, int):
        level = f"{level:03d}"
    elif isinstance(level, str):
        level = level.zfill(3)
    else:
        return jsonify({'error': 'Invalid level format'}), 400

    try:
        # Create a temporary directory to store the plot
        with tempfile.TemporaryDirectory() as temp_dir:
            # Generate plot for the requested level
            plot_files = generate_wind_plots(departure, arrival, [level], temp_dir)
            if not plot_files or not os.path.exists(plot_files[0]):
                return jsonify({'error': 'Failed to generate wind plot'}), 500

            plot_file = plot_files[0]
            # Send the SVG file
            response = make_response(send_file(
                plot_file,
                mimetype='image/svg+xml',
                as_attachment=True,
                download_name=os.path.basename(plot_file)
            ))
            # CORS headers are set globally in after_request
            return response

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/wind-data-augmented', methods=['POST'])
def get_wind_data_augmented():
    # Accept both JSON and form data for flexibility
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form.to_dict()

    # Validate input
    required_params = ['departure', 'arrival', 'level']
    if not data or not all(param in data for param in required_params):
        return jsonify({'error': f'Missing required parameters: {", ".join(required_params)}'}), 400

    # Set default values for magnitude_factor and angle_factor if not provided
    magnitude_factor = data.get('magnitude_factor', 1.5)
    angle_factor = data.get('angle_factor', 2)
        
    departure = data['departure']
    arrival = data['arrival']
    level = data['level']
    
    # Convert and validate magnitude_factor and angle_factor
    try:
        magnitude_factor = float(magnitude_factor)
        angle_factor = float(angle_factor)
        
        if magnitude_factor <= 0:
            return jsonify({'error': 'magnitude_factor must be positive'}), 400
            
    except ValueError:
        return jsonify({'error': 'Invalid magnitude_factor or angle_factor format'}), 400

    # Accept level as a string, or as an int (convert to string with leading zeros)
    if isinstance(level, int):
        level = f"{level:03d}"
    elif isinstance(level, str):
        level = level.zfill(3)
    else:
        return jsonify({'error': 'Invalid level format'}), 400

    try:
        # Create a temporary directory to store the plot
        with tempfile.TemporaryDirectory() as temp_dir:
            # Generate augmented plot for the requested level
            plot_files = generate_wind_plots_augmented(
                departure, arrival, [level], temp_dir,
                magnitude_factor, angle_factor
            )
            
            if not plot_files or not os.path.exists(plot_files[0]):
                return jsonify({'error': 'Failed to generate augmented wind plot'}), 500

            plot_file = plot_files[0]
            # Send the SVG file
            response = make_response(send_file(
                plot_file,
                mimetype='image/svg+xml',
                as_attachment=True,
                download_name=os.path.basename(plot_file)
            ))
            # CORS headers are set globally in after_request
            return response

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Hardcoded WebSocket channel
HARDCODED_CHANNEL = "wss://s14544.blr1.piesocket.com/v3/1?api_key=iJshgbsdZocGM142oxMQ3XxtKzAcfs9sru2aBVuH&notify_self=1"

def publish_to_channel(message):
    # Send the message to the hardcoded websocket channel using websockets.sync.client.connect
    try:
        # Convert message to JSON string if it's not already a string
        if not isinstance(message, str):
            message = json.dumps(message)
        with connect(HARDCODED_CHANNEL) as websocket:
            websocket.send(message)
            # Optionally, receive a response (not required, but for demonstration)
            try:
                response = websocket.recv()
                print(f"Received from WS: {response}")
            except Exception:
                pass
    except Exception as e:
        print(f"Error sending message to websocket: {e}")

@app.route('/publish', methods=['POST'])
def publish():
    """
    Accepts JSON with 'data', and publishes 'data' to the hardcoded websocket channel.
    Example input:
    {
        "data": { ... }
    }
    """
    try:
        payload = request.get_json(force=True)
        data = payload.get('data')
        if data is None:
            return jsonify({'error': 'Missing data'}), 400

        # Publish the data to the hardcoded channel
        publish_to_channel(data)

        return jsonify({'status': 'published', 'channel': HARDCODED_CHANNEL}), 200
    except Exception as e:
        app.logger.error(f"Error in /publish: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/', methods=['GET'])
def index():
    try:
        response = jsonify({
            'message': 'Wind Data API',
            'status': 'OK',
            'endpoints': {
                'wind-data': {
                    'method': 'POST',
                    'parameters': {
                        'departure': 'ICAO airport code (e.g., KSMO)',
                        'arrival': 'ICAO airport code (e.g., KJFK)',
                        'level': 'Flight level (e.g., "030" or 30)'
                    },
                    'returns': 'SVG image file'
                },
                'wind-data-augmented': {
                    'method': 'POST',
                    'parameters': {
                        'departure': 'ICAO airport code (e.g., KSMO)',
                        'arrival': 'ICAO airport code (e.g., KJFK)',
                        'level': 'Flight level (e.g., "030" or 30)',
                        'magnitude_factor': 'Factor to multiply wind speeds (e.g., 1.5)',
                        'angle_factor': 'Factor to add to wind direction proportional to speed (e.g., 0.5)'
                    },
                    'returns': 'SVG image file with both original and augmented winds'
                }
            }
        })
        # CORS headers are set globally in after_request
        return response
    except Exception as e:
        app.logger.error(f"Error in index route: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=3001, host='0.0.0.0')