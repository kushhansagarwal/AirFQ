# Wind Data Visualization API

This API generates wind data visualizations for flight routes between two airports at different flight levels.

## Setup

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
Create a `.env` file with your API key:
```
AIRPORT_KEY=your_api_ninjas_key_here
```

3. Run the API:
```bash
python api.py
```

## API Usage

The API exposes a single endpoint that accepts POST requests:

**Endpoint:** `/wind-data`

**Method:** POST

**Request Body:**
```json
{
    "departure": "KSMO",
    "arrival": "KJFK"
}
```

**Response:**
- A zip file containing wind data plots for 5 different flight levels (FL030, FL050, FL070, FL090, FL120)
- Each plot shows wind vectors along the route between the specified airports

**Example using curl:**
```bash
curl -X POST -H "Content-Type: application/json" \
     -d '{"departure":"KSMO","arrival":"KJFK"}' \
     http://localhost:5000/wind-data -o wind_plots.zip
```

## Features

- Generates wind data visualizations for 5 different flight levels
- Uses real-time weather data from Aviation Weather Center
- Includes airport information from API Ninjas
- Creates detailed maps with:
  - Airport markers and labels
  - Wind vectors showing direction and speed
  - Route line between airports
  - Coastlines, country borders, and state boundaries
  - Latitude/longitude grid 