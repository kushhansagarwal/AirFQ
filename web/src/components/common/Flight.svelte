<script lang="ts">
  // Mock flight data - in a real app, this would come from an API or props
  const flight = {
    flightNumber: "UA1234",
    startAirport: {
      code: "KSFO",
      name: "San Francisco International Airport"
    },
    endAirport: {
      code: "KJFK",
      name: "John F. Kennedy International Airport"
    },
    status: "In Progress",
    windSpeed: "25 knots",
    airSpeed: "480 knots",
    location: {
      lat: 39.8283,
      lng: -98.5795,
      description: "Over Kansas City, MO"
    },
    temperature: {
      outside: "-45°C",
      cabin: "21°C"
    },
    reportingSince: new Date(Date.now() - 3600000), // 1 hour ago
    forecastDeviation: "Minor - 15 min delay expected",
    reportedHazards: [
      "PIREP UA /OV DEN 090025 /TM 1516 /FL 210 /TP B738 /TB MOD",
      "PIREP UA /OV ORD 270030 /TM 1445 /FL 180 /TP A320 /SK BKN070-TOP110 /TA -15",
      "PIREP UUA /OV JOT 320015 /TM 1430 /FL 090 /TP CRJ2 /IC MOD-SEV RIME"
    ]
  };

  // Format the reporting time
  const formatTime = (date: Date): string => {
    return date.toLocaleTimeString('en-US', { 
      hour: '2-digit', 
      minute: '2-digit',
      hour12: true 
    });
  };

  const formatDate = (date: Date): string => {
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
  };

  // Determine status color
  const getStatusColor = (status: string): string => {
    switch(status.toLowerCase()) {
      case 'completed': return 'success';
      case 'delayed': return 'warning';
      case 'cancelled': return 'error';
      case 'in progress': return 'info';
      default: return 'primary';
    }
  };
</script>

<div class="p-4 max-w-4xl mx-auto">
  <div class="card bg-base-100 shadow-xl">
    <!-- Header with flight number and airports -->
    <div class="card-body">
      <div class="flex flex-col md:flex-row justify-between items-start md:items-center">
        <div>
          <h2 class="card-title text-2xl font-bold">{flight.flightNumber}</h2>
          <p class="text-base-content/70">
            {formatDate(flight.reportingSince)} • Reporting since {formatTime(flight.reportingSince)}
          </p>
        </div>
        <div class="badge badge-{getStatusColor(flight.status)} badge-lg mt-2 md:mt-0">
          {flight.status}
        </div>
      </div>

      <!-- Flight route visualization -->
      <div class="my-6 flex items-center justify-between">
        <div class="text-center">
          <div class="text-2xl font-bold">{flight.startAirport.code}</div>
          <div class="text-sm text-base-content/70">{flight.startAirport.name}</div>
        </div>
        
        <div class="flex-1 mx-4 relative">
          <div class="h-1 bg-base-300 w-full"></div>
          <div class="absolute w-3 h-3 bg-primary rounded-full" style="left: 40%; top: -4px;"></div>
          <div class="text-xs text-center mt-2">{flight.location.description}</div>
        </div>
        
        <div class="text-center">
          <div class="text-2xl font-bold">{flight.endAirport.code}</div>
          <div class="text-sm text-base-content/70">{flight.endAirport.name}</div>
        </div>
      </div>

      <!-- Flight stats -->
      <div class="stats stats-vertical lg:stats-horizontal shadow w-full my-4">
        <div class="stat">
          <div class="stat-title">Wind Speed</div>
          <div class="stat-value text-lg">{flight.windSpeed}</div>
        </div>
        
        <div class="stat">
          <div class="stat-title">Air Speed</div>
          <div class="stat-value text-lg">{flight.airSpeed}</div>
        </div>
        
        <div class="stat">
          <div class="stat-title">Outside Temp</div>
          <div class="stat-value text-lg">{flight.temperature.outside}</div>
        </div>
        
        <div class="stat">
          <div class="stat-title">Cabin Temp</div>
          <div class="stat-value text-lg">{flight.temperature.cabin}</div>
        </div>
      </div>

      <!-- Location and forecast -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4 my-4">
        <div class="card bg-base-200">
          <div class="card-body">
            <h3 class="card-title text-lg">Current Location</h3>
            <p>Latitude: {flight.location.lat}</p>
            <p>Longitude: {flight.location.lng}</p>
            <p>{flight.location.description}</p>
          </div>
        </div>
        
        <div class="card bg-base-200">
          <div class="card-body">
            <h3 class="card-title text-lg">Forecast Deviation</h3>
            <p>{flight.forecastDeviation}</p>
          </div>
        </div>
      </div>

      <!-- Reported hazards -->
      <div class="my-4">
        <h3 class="text-lg font-bold mb-2">Reported Hazards (PIREPs)</h3>
        <div class="bg-base-200 p-4 rounded-lg">
          <ul class="space-y-2">
            {#each flight.reportedHazards as hazard}
              <li class="p-2 bg-base-100 rounded border-l-4 border-warning font-mono text-sm">
                {hazard}
              </li>
            {/each}
          </ul>
        </div>
      </div>

      <!-- PIREP legend -->
      <div class="collapse collapse-arrow bg-base-200 my-4">
        <input type="checkbox" /> 
        <div class="collapse-title font-medium">
          PIREP Code Legend
        </div>
        <div class="collapse-content text-sm"> 
          <p><strong>UA</strong> - Routine PIREP</p>
          <p><strong>UUA</strong> - Urgent PIREP</p>
          <p><strong>OV</strong> - Location</p>
          <p><strong>TM</strong> - Time</p>
          <p><strong>FL</strong> - Flight Level</p>
          <p><strong>TP</strong> - Aircraft Type</p>
          <p><strong>SK</strong> - Sky Condition</p>
          <p><strong>TA</strong> - Temperature</p>
          <p><strong>TB</strong> - Turbulence</p>
          <p><strong>IC</strong> - Icing</p>
        </div>
      </div>
    </div>
  </div>
</div>
