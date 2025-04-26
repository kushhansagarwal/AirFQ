import asyncio
import json
import websockets
import random
import time
import math
from datetime import datetime

# Configuration for the WebSocket server
HOST = "localhost"
PORT = 8765

# Flight data generator
class FlightDataGenerator:
    def __init__(self, flight_id=None, lat=None, lon=None):
        self.flight_id = flight_id if flight_id else f"FL{random.randint(1000, 9999)}"
        self.lat = lat if lat is not None else random.uniform(30.0, 50.0)  # Starting latitude
        self.lon = lon if lon is not None else random.uniform(-120.0, -70.0)  # Starting longitude

        # Initial values for other parameters
        self.oat = random.uniform(-20.0, 30.0)  # Outside Air Temperature (°C)
        self.ias = random.uniform(200.0, 300.0)  # Indicated Airspeed (knots)
        self.tas = random.uniform(250.0, 350.0)  # True Airspeed (knots)
        self.track = random.uniform(0.0, 359.9)  # Track (degrees)
        self.heading = random.uniform(0.0, 359.9)  # Heading (degrees)
        self.gs = random.uniform(400.0, 500.0)  # Ground Speed (knots)
        self.humidity = random.uniform(10.0, 90.0)  # Humidity (%)

        # New metric: speed_factor, controls how far/fast the lat/lon moves per update
        self.speed_factor = 50

        # For smooth path: define a direction and a curvature
        self._base_step_size = random.uniform(0.01, 0.03)  # base degrees per update
        self._step_size = self._base_step_size * self.speed_factor  # actual step size
        self._base_direction = random.uniform(0, 2 * math.pi)  # radians
        self._curvature = random.uniform(-0.002, 0.002)  # radians per update
        self._step_count = 0

        # Store previous lat/lon for heading calculation
        self._prev_lat = self.lat
        self._prev_lon = self.lon

    def _calculate_heading(self, lat1, lon1, lat2, lon2):
        """
        Calculate the heading (initial bearing) from (lat1, lon1) to (lat2, lon2).
        All args in degrees. Returns heading in degrees (0 = North, 90 = East).
        """
        # Convert to radians
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        dlon_rad = math.radians(lon2 - lon1)
        x = math.sin(dlon_rad) * math.cos(lat2_rad)
        y = math.cos(lat1_rad) * math.sin(lat2_rad) - \
            math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlon_rad)
        initial_bearing = math.atan2(x, y)
        # Convert from radians to degrees and normalize
        bearing_deg = (math.degrees(initial_bearing) + 360) % 360
        return bearing_deg

    def generate_data(self):
        # Optionally, allow speed_factor to drift a little over time
        self.speed_factor += random.uniform(-0.02, 0.02)
        self.speed_factor = max(0.2, min(3.0, self.speed_factor))  # Clamp to reasonable range

        # Update step size based on speed_factor
        self._step_size = self._base_step_size * self.speed_factor

        # Simulate smooth movement along a curved path
        # The direction changes slowly over time to create a gentle curve
        direction = self._base_direction + self._curvature * self._step_count
        delta_lat = self._step_size * math.cos(direction)
        delta_lon = self._step_size * math.sin(direction)
        new_lat = self.lat + delta_lat
        new_lon = self.lon + delta_lon

        # Calculate heading based on movement from previous to new position
        heading = self._calculate_heading(self.lat, self.lon, new_lat, new_lon)

        # Update position and step count
        self._prev_lat = self.lat
        self._prev_lon = self.lon
        self.lat = new_lat
        self.lon = new_lon
        self._step_count += 1

        # Random walk for other parameters with low variations
        self.oat += random.uniform(-0.5, 0.5)
        self.ias += random.uniform(-2.0, 2.0)
        self.tas += random.uniform(-2.0, 2.0)
        self.track += random.uniform(-1.0, 1.0)
        self.gs += random.uniform(-3.0, 3.0)
        self.humidity += random.uniform(-1.0, 1.0)

        # Keep values within reasonable ranges
        self.track %= 360
        self.humidity = max(10.0, min(90.0, self.humidity))

        # The heading now reflects the actual direction of movement
        self.heading = heading

        return {
            "flightId": self.flight_id,
            "oat": self.oat,
            "ias": self.ias,
            "tas": self.tas,
            "track": self.track,
            "heading": self.heading,
            "gs": self.gs,
            "humidity": self.humidity,
            "speedFactor": self.speed_factor,  # Include the new metric in the output
            "timestamp": int(time.time() * 1000),
            "lat": self.lat,
            "lon": self.lon
        }

# WebSocket handler
async def flight_data_server(websocket):  # Removed the path parameter
    # Create three flight generators with defined initial parameters
    flight_generators = [
        FlightDataGenerator(flight_id="N32169", lat=40.7128, lon=-74.0060),  # New York
        FlightDataGenerator(flight_id="N777VP", lat=34.0522, lon=-118.2437),  # Los Angeles
        FlightDataGenerator(flight_id="N400JW", lat=41.8781, lon=-87.6298)   # Chicago
    ]
    
    try:
        print(f"Client connected: {websocket.remote_address}")
        while True:
            for generator in flight_generators:
                # Generate flight data
                flight_data = generator.generate_data()
                
                # Convert to JSON and send
                await websocket.send(json.dumps(flight_data))
                
                # Small delay between each flight's data
                await asyncio.sleep(0.1)
            
            # Wait before sending next update for all flights
            await asyncio.sleep(0.1)
    except websockets.exceptions.ConnectionClosed:
        print(f"Client disconnected: {websocket.remote_address}")

# Main function to start the server
async def main():
    server = await websockets.serve(flight_data_server, HOST, PORT)
    print(f"WebSocket server started at ws://{HOST}:{PORT}")
    await server.wait_closed()

# Run the server
if __name__ == "__main__":
    asyncio.run(main())