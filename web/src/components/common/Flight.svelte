<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	
	const { flightInfo } = $props();

	// Flight data structure with default values
	let flight = $state({
		flightNumber: flightInfo.flightId,
		startAirport: {
			code: flightInfo.departureAirport,
			name: getAirportFullName(flightInfo.departureAirport)
		},
		endAirport: {
			code: flightInfo.arrivalAirport,
			name: getAirportFullName(flightInfo.arrivalAirport)
		},
		status: 'In Progress',
		windSpeed: '0 knots',
		airSpeed: '0 knots',
		location: {
			lat: 0,
			lng: 0,
			description: 'Connecting...'
		},
		temperature: {
			outside: '0°C',
			cabin: '21°C'
		},
		reportingSince: new Date(),
		forecastDeviation: 'Connecting to flight data...',
		reportedHazards: [
			'Connecting to flight data...'
		]
	});

	let socket: WebSocket;
	let connected = $state(false);

	// Function to get airport full name based on code
	function getAirportFullName(code: string): string {
		const airports: Record<string, string> = {
			'KSFO': 'San Francisco International Airport',
			'KJFK': 'John F. Kennedy International Airport',
			'KLAX': 'Los Angeles International Airport',
			'KORD': 'O\'Hare International Airport',
			'KATL': 'Hartsfield-Jackson Atlanta International Airport'
		};
		
		return airports[code] || code;
	}

	// Format the reporting time
	function formatTime(date: Date): string {
		return date.toLocaleTimeString('en-US', {
			hour: '2-digit',
			minute: '2-digit',
			hour12: true
		});
	}

	function formatDate(date: Date): string {
		return date.toLocaleDateString('en-US', {
			month: 'short',
			day: 'numeric',
			year: 'numeric'
		});
	}

	// Determine status color
	function getStatusColor(status: string): string {
		switch (status.toLowerCase()) {
			case 'completed':
				return 'success';
			case 'delayed':
				return 'warning';
			case 'cancelled':
				return 'error';
			case 'in progress':
				return 'info';
			default:
				return 'primary';
		}
	}

	// Connect to WebSocket and update flight data
	onMount(() => {
		connectWebSocket();
	});

	onDestroy(() => {
		if (socket) {
			socket.close();
		}
	});

	function connectWebSocket() {
		socket = new WebSocket('ws://localhost:8765');
		
		socket.onopen = () => {
			connected = true;
			console.log('WebSocket connected');
		};
		
		socket.onmessage = (event) => {
			const data = JSON.parse(event.data);
			
			// Only update if this message is for our flight
			if (data.flightId === flightInfo.flightId) {
				updateFlightData(data);
			}
		};
		
		socket.onerror = (error) => {
			console.error('WebSocket error:', error);
		};
		
		socket.onclose = () => {
			connected = false;
			console.log('WebSocket disconnected');
			
			// Try to reconnect after a delay
			setTimeout(connectWebSocket, 5000);
		};
	}

	function updateFlightData(data: any) {
		flight = {
			...flight,
			windSpeed: `${Math.round(data.gs - data.tas)} knots`,
			airSpeed: `${Math.round(data.tas)} knots`,
			location: {
				lat: data.lat,
				lng: data.lon,
				description: `Heading ${Math.round(data.heading)}° at ${Math.round(data.gs)} knots`
			},
			temperature: {
				outside: `${Math.round(data.oat)}°C`,
				cabin: '21°C'
			},
			reportingSince: new Date(data.timestamp || Date.now())
		};
	}
</script>

<div class="">
	<div class="bg-base-100">
		<!-- Header with flight number and airports -->
		<div class="card-body">
			<div class="flex flex-col items-start justify-between md:flex-row md:items-center">
				<div>
					<h2 class="card-title text-2xl font-bold">{flightInfo.flightId}</h2>
					<p class="text-base-content/70">
						{formatDate(flight.reportingSince)} • Reporting since {formatTime(
							flight.reportingSince
						)}
					</p>
				</div>
				<div class="badge badge-lg mt-2 md:mt-0 border-2 
					{connected ? 'border-success text-success' : 
					 'border-warning text-warning'}">
					{connected ? 'Live' : 'Waiting'}
				</div>
			</div>

			<!-- Flight route visualization -->
			<div class="my-6 flex items-center justify-between">
				<div class="text-center">
					<div class="text-2xl font-bold">{flight.startAirport.code}</div>
					<div class="text-base-content/70 text-sm">{flight.startAirport.name}</div>
				</div>

				<div class="relative mx-4 flex-1">
					<div class="bg-base-300 h-1 w-full"></div>
					<div class="bg-primary absolute h-3 w-3 rounded-full" style="left: 40%; top: -4px;"></div>
					<div class="mt-2 text-center text-xs">{flight.location.description}</div>
				</div>

				<div class="text-center">
					<div class="text-2xl font-bold">{flight.endAirport.code}</div>
					<div class="text-base-content/70 text-sm">{flight.endAirport.name}</div>
				</div>
			</div>

			<!-- Flight stats -->
			<div class="stats stats-vertical lg:stats-horizontal my-4 w-full shadow">
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
			<div class="my-4 grid grid-cols-1 gap-4 md:grid-cols-2">
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
				<h3 class="mb-2 text-lg font-bold">Reported Hazards (PIREPs)</h3>
				<div class="bg-base-200 rounded-lg p-4">
					<ul class="space-y-2">
						{#each flight.reportedHazards as hazard}
							<li class="bg-base-100 border-warning rounded border-l-4 p-2 font-mono text-sm">
								{hazard}
							</li>
						{/each}
					</ul>
				</div>
			</div>

			<!-- PIREP legend -->
			<div class="collapse-arrow bg-base-200 collapse my-4">
				<input type="checkbox" />
				<div class="collapse-title font-medium">PIREP Code Legend</div>
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
