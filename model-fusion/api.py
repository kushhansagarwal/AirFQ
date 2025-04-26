from flask import Flask, request, jsonify, send_file, make_response
import os
from main import generate_wind_plots
import tempfile
from werkzeug.utils import secure_filename
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

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
            # Add CORS headers explicitly (in case CORS(app) is not enough)
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
            response.headers['Access-Control-Allow-Methods'] = 'POST,OPTIONS'
            return response

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.after_request
def after_request(response):
    # Ensure CORS headers are set for all responses
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
    return response

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
                }
            }
        })
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    except Exception as e:
        app.logger.error(f"Error in index route: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')