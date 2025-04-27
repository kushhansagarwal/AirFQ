<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
    import Map from './Map.svelte';
	import { PUBLIC_TRAFFIC_URL } from '$env/static/public';
	const { flightInfo } = $props();

	let data: any = $state(null);
	let socket: WebSocket;

	// Airport code to name
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

	// Calculate wind speed and direction from metrics
	function getWind(data: any) {
		// Convert degrees to radians
		const toRad = (deg: number) => deg * Math.PI / 180;
		const toDeg = (rad: number) => (rad * 180 / Math.PI + 360) % 360;

		const gs = data.gs;
		const tas = data.tas;
		const track = toRad(data.track);
		const heading = toRad(data.heading);

		// Wind triangle
		const wx = gs * Math.sin(track) - tas * Math.sin(heading);
		const wy = gs * Math.cos(track) - tas * Math.cos(heading);

		const windSpeed = Math.sqrt(wx * wx + wy * wy);
		const windDir = (toDeg(Math.atan2(wx, wy)) + 180) % 360; // FROM direction

		return {
			speed: windSpeed,
			dir: windDir
		};
	}

	let wind: any = $state(null);
	$effect(() => {
		if (data) {
			wind = getWind(data);
		}
	});

	let updateCount = $state(0);
	let mapKey = $state(0);

	onMount(() => {
		connectWebSocket();
	});

	onDestroy(() => {
		if (socket) socket.close();
	});

	function connectWebSocket() {
		socket = new WebSocket(PUBLIC_TRAFFIC_URL);
		socket.onmessage = (event) => {
			const msg = JSON.parse(event.data);
			if (msg.flightId === flightInfo.flightId) {
				data = msg;
				updateCount += 1;
				if (updateCount % 5 === 0) {
					mapKey += 1;
				}
			}
		};
		socket.onclose = () => setTimeout(connectWebSocket, 5000);
	}
</script>

{#if data}
<div class="bg-base-100 p-6 rounded-lg shadow w-full max-w-xl mx-auto">
	<div class="flex flex-col items-center gap-2 mb-6">
		<h2 class="text-2xl font-bold">{flightInfo.flightId}</h2>
		<div class="text-base-content/70 text-sm">
			{#if data.timestamp}
				{new Date(data.timestamp).toLocaleString()}
			{/if}
		</div>
	</div>

	<!-- Route with plane icon -->
	<div class="flex items-center justify-between mb-8">
		<div class="text-center w-32">
			<div class="text-2xl font-bold">{flightInfo.departureAirport}</div>
			<div class="text-xs text-base-content/70">{getAirportFullName(flightInfo.departureAirport)}</div>
		</div>
		<div class="flex-1 flex flex-col items-center relative">
			<!-- <div class="bg-base-300 h-1 w-full absolute top-1/2 left-0" style="transform: translateY(-50%);"></div> -->
			<!-- Plane icon, rotated by heading -->
			<div class="z-10" style="transform: rotate({data.heading || 0}deg); transition: transform 0.3s;">
				<img src="/flight.svg   " alt="Plane" width="40" height="40" />
			</div>
		</div>
		<div class="text-center w-32">
			<div class="text-2xl font-bold">{flightInfo.arrivalAirport}</div>
			<div class="text-xs text-base-content/70">{getAirportFullName(flightInfo.arrivalAirport)}</div>
		</div>
	</div>

	<!-- Stats -->
	<div class="grid grid-cols-1 md:grid-cols-3 gap-6">
		<!-- Wind Speed with arrow -->
		<div class="flex flex-col items-center">
			<div class="flex items-center gap-2 mb-1">
				<span class="text-sm font-semibold">Wind</span>
				{#if wind}
					<!-- Wind direction arrow, rotate by wind.dir -->
					<span style="display:inline-block;transform:rotate({wind.dir}deg);transition:transform 0.3s;">
						<img src="/arrow.svg" alt="Wind direction" width="22" height="22" />
					</span>
				{/if}
			</div>
			<div class="text-lg font-mono">
				{#if wind}{Math.round(wind.speed)} knots{/if}
			</div>
			<div class="text-xs text-base-content/70">
				{#if wind}From {Math.round(wind.dir)}°{/if}
			</div>
		</div>
		<!-- True Airspeed -->
		<div class="flex flex-col items-center">
			<div class="text-sm font-semibold mb-1">True Airspeed</div>
			<div class="text-lg font-mono">{Math.round(data.tas)} knots</div>
			<div class="text-xs text-base-content/70">Heading {Math.round(data.heading)}°</div>
		</div>
		<!-- Ground Speed -->
		<div class="flex flex-col items-center">
			<div class="text-sm font-semibold mb-1">Ground Speed</div>
			<div class="text-lg font-mono">{Math.round(data.gs)} knots</div>
			<div class="text-xs text-base-content/70">Track {Math.round(data.track)}°</div>
		</div>
	</div>

	<!-- Outside Temp & Humidity -->
	<div class="grid grid-cols-2 gap-6 mt-8 mb-8">
		<div class="flex flex-col items-center">
			<div class="text-sm font-semibold mb-1">Outside Temp</div>
			<div class="text-lg font-mono">{Math.round(data.oat)}°C</div>
		</div>
		<div class="flex flex-col items-center">
			<div class="text-sm font-semibold mb-1">Humidity</div>
			<div class="text-lg font-mono">{Math.round(data.humidity)}%</div>
		</div>
	</div>

    {#key mapKey}
        <Map lat={data.lat} lon={data.lon} heading={data.heading} />
    {/key}
</div>
{:else}
<div class="flex items-center justify-center h-64 text-base-content/60">
	Connecting to flight data...
</div>
{/if}
