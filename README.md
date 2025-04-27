![AirFQ Banner](web/static/banner.png)
![Image Banner](banner.png)

# AirFQ
Airborne Information Reporting - Flight Qualified

## Overview

A suite of tools to collect location, airspeed, humidity, temperature and other data from airborne planes in an area and render it in a dashboard. This data is fused with existing weather models to predict accuracy, changes, hazards and other critical information. This data is also shown in real-time to pilots to enhance the in-flight experience.

## Testing

How do I know this works? I tried it out in the air. Crazy? I was crazy once, They locked me in a room, a rubber room, a rubber room with rats, and rats make me crazy.

### High Speed Taxi Check
I requested a taxi from the hangar down the runway, reaching 70 knots and then slowing down to exit the runway.
![High Speed Taxi Check](/unit-parser/taxi/maps_subplot.png)

### Flight Test
I took off and climbed to 1400 feet, then flew a right hand pattern to end up back at the airport. Airspeed was only measured uptil a point before turning right base for runway 21.
![Flight Test](/unit-parser/flight/maps_subplot.png)


## Project Structure

- `/simulator` - Python-based flight data simulator
- `/web` - SvelteKit web dashboard
- `/whitepaper` - Technical documentation and mathematical formulation
- `/unit-parser` - Python-based unit parser
- `/unit-parser/flight` - Flight data for the flight test
- `/unit-parser/taxi` - Flight data for the taxi test
- `/flight-units` - Flight units for the flight test

## Setup Instructions

### Flight Simulator

1. Create a Python virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install Python dependencies:
```bash
pip install websockets asyncio
```

3. Run the simulator:
```bash
cd simulator
python main.py
```

The simulator will start a WebSocket server at `ws://localhost:8765`

### Web Dashboard

1. Install Node.js dependencies:
```bash
cd web
npm install
```

2. Start the development server:
```bash
npm run dev
```

The web dashboard will be available at `http://localhost:5173`

## [Technical Details](whitepaper/AirFQ.pdf)

The project implements a real-time flight data augmentation system using Kalman filtering. The mathematical formulation and implementation details can be found in the whitepaper directory.

Key features:
- Real-time flight data collection via WebSocket
- Dynamic weather model augmentation
- Interactive flight route planning
- Temperature, humidity, and airspeed visualization
- Integration with existing weather models

## Environment Variables

The web dashboard requires the following environment variables:
```
GOOGLE_MAPS_API_KEY=your_api_key  # Required for route visualization
```

Create a `.env` file in the `/web` directory with these variables.

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request


## Acknowledgements

Some code from previous projects was reused, specifically:

- Experience with the [AviationWeather.gov](https://www.aviationweather.gov/) API and a program to create wind charts

## License

This project is licensed under the MIT License - see the LICENSE file for details.

