#!/usr/bin/env python

from flask import Flask, request, jsonify, send_file, make_response
import os
from main import generate_and_upload_wind_plot
import tempfile
from werkzeug.utils import secure_filename
from websockets.sync.client import connect
import json
import threading
from flask_cors import CORS
import logging
import gc
from werkzeug.middleware.proxy_fix import ProxyFix
import uuid
import boto3
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("api.log")
    ]
)
logger = logging.getLogger(__name__)

# S3 Configuration
S3_BUCKET = os.environ.get('S3_BUCKET', 'airfq')
S3_REGION = os.environ.get('AWS_REGION', 'us-west-2')
S3_URL_EXPIRATION = 604800  # 7 days in seconds

# Initialize S3 client
s3 = boto3.client(
    's3',
    aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
    region_name=S3_REGION
)

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
CORS(app)  # Enable CORS for all routes

def upload_file_to_s3(file_path, bucket, object_name=None):
    """Upload a file to S3 bucket and return the URL"""
    if object_name is None:
        # Use timestamp and UUID for unique filename
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        random_id = str(uuid.uuid4())[:8]
        object_name = f"wind-plots/{timestamp}-{random_id}-{os.path.basename(file_path)}"

    try:
        # Set content type for viewable images
        content_type = 'image/png'
        
        # Upload file to S3 with content type and content disposition headers
        s3.upload_file(
            file_path, 
            bucket, 
            object_name,
            ExtraArgs={
                'ContentType': content_type,
                'ContentDisposition': 'inline'  # This makes it viewable in browser
            }
        )
        
        # Generate URL
        url = f"https://{bucket}.s3.{S3_REGION}.amazonaws.com/{object_name}"
        return url
    except Exception as e:
        logger.error(f"Error uploading to S3: {str(e)}")
        raise

@app.route('/wind-data', methods=['POST'])
def get_wind_data():
    try:
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict()
        if not data or 'departure' not in data or 'arrival' not in data or 'level' not in data:
            return jsonify({'error': 'Missing required parameters (departure, arrival, level)'}), 400
        departure = data['departure']
        arrival = data['arrival']
        level = data['level']
        # Always generate low-res
        s3_url = generate_and_upload_wind_plot(departure, arrival, level, low_res=True, augmented=False)
        return jsonify({
            'status': 'success',
            'url': s3_url,
            'departure': departure,
            'arrival': arrival,
            'level': level
        })
    except Exception as e:
        logger.exception(f"Error in wind-data endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/wind-data-augmented', methods=['POST'])
def get_wind_data_augmented():
    try:
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict()
        required_params = ['departure', 'arrival', 'level']
        if not data or not all(param in data for param in required_params):
            return jsonify({'error': f'Missing required parameters: {", ".join(required_params)}'}), 400
        departure = data['departure']
        arrival = data['arrival']
        level = data['level']
        magnitude_factor = float(data.get('magnitude_factor', 1.5))
        angle_factor = float(data.get('angle_factor', 0.5))
        # Always generate low-res
        s3_url = generate_and_upload_wind_plot(
            departure, arrival, level,
            magnitude_factor=magnitude_factor,
            angle_factor=angle_factor,
            low_res=True,
            augmented=True
        )
        return jsonify({
            'status': 'success',
            'url': s3_url,
            'departure': departure,
            'arrival': arrival,
            'level': level,
            'magnitude_factor': magnitude_factor,
            'angle_factor': angle_factor
        })
    except Exception as e:
        logger.exception(f"Error in wind-data-augmented endpoint: {str(e)}")
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
                        'level': 'Flight level (e.g., "030" or 30)',
                        'max_pixels': 'Maximum image dimension in pixels (default: 2000)'
                    },
                    'returns': 'JSON with S3 URL to the generated PNG'
                },
                'wind-data-augmented': {
                    'method': 'POST',
                    'parameters': {
                        'departure': 'ICAO airport code (e.g., KSMO)',
                        'arrival': 'ICAO airport code (e.g., KJFK)',
                        'level': 'Flight level (e.g., "030" or 30)',
                        'magnitude_factor': 'Factor to multiply wind speeds (default: 1.5)',
                        'angle_factor': 'Factor to add to wind direction proportional to speed (default: 0.5)',
                        'max_pixels': 'Maximum image dimension in pixels (default: 2000)'
                    },
                    'returns': 'JSON with S3 URL to the generated PNG'
                }
            }
        })
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    except Exception as e:
        logger.exception(f"Error in index route: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Hardcoded WebSocket channel
HARDCODED_CHANNEL = "wss://s14544.blr1.piesocket.com/v3/kushagarwal?api_key=iJshgbsdZocGM142oxMQ3XxtKzAcfs9sru2aBVuH"

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
    Accepts JSON with 'data', and initiates publishing 'data' to the hardcoded websocket channel.
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

        # Initiate publishing the data to the hardcoded channel without waiting for completion
        threading.Thread(target=publish_to_channel, args=(data,)).start()

        return jsonify({'status': 'publishing initiated', 'channel': HARDCODED_CHANNEL}), 200
    except Exception as e:
        logger.error(f"Error in /publish: {str(e)}")
        return jsonify({'error': str(e)}), 500

def create_app():
    """Factory function for creating the app instance"""
    return app

if __name__ == '__main__':
    # Development server
    app.run(debug=False, port=3001, host='0.0.0.0', threaded=True)
else:
    # Production mode when imported by a WSGI server
    # Set up production-specific configurations
    app.config['ENV'] = 'production'
    app.config['DEBUG'] = False