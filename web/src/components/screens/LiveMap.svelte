<script lang="ts">
	import { onMount } from 'svelte';
	let flights: Record<string, any> = {};

	let canvas: HTMLCanvasElement;
	let ctx: CanvasRenderingContext2D | null = null;

	// Map boundaries (for a simple equirectangular projection)
	const MAP = {
		latMin: 24.396308,  // Southernmost point in contiguous US
		latMax: 49.384358,  // Northernmost point in contiguous US
		lonMin: -125.0,     // Westernmost point in contiguous US
		lonMax: -66.93457   // Easternmost point in contiguous US
	};

	const CANVAS_WIDTH = 1000;
	const CANVAS_HEIGHT = 550;

	let dpr = 1;

	// Flight trails: { [flightId]: Array<{lat, lon}> }
	let trails: Record<string, Array<{ lat: number, lon: number }>> = {};

	// Only define planeImg and mapImg on the client (browser)
	let planeImg: HTMLImageElement | null = null;
	let mapImg: HTMLImageElement | null = null;

	function latLonToXY(lat: number, lon: number) {
		const x = ((lon - MAP.lonMin) / (MAP.lonMax - MAP.lonMin)) * CANVAS_WIDTH;
		const y = CANVAS_HEIGHT - ((lat - MAP.latMin) / (MAP.latMax - MAP.latMin)) * CANVAS_HEIGHT;
		return { x, y };
	}

	function drawFlights() {
		if (!ctx) return;
		ctx.clearRect(0, 0, CANVAS_WIDTH * dpr, CANVAS_HEIGHT * dpr);

		// Draw the map background if loaded
		if (mapImg && mapImg.complete && mapImg.naturalWidth > 0) {
			ctx.drawImage(
				mapImg,
				0, 0,
				CANVAS_WIDTH * dpr,
				CANVAS_HEIGHT * dpr
			);
		}

		// Draw all flight trails first
		for (const flightId in trails) {
			const trail = trails[flightId];
			if (!trail || trail.length < 2) continue;
			ctx.save();
			ctx.strokeStyle = "#1976d2";
			ctx.lineWidth = 3 * dpr;
			ctx.globalAlpha = 0.7;
			ctx.beginPath();
			for (let i = 0; i < trail.length; i++) {
				const { x, y } = latLonToXY(trail[i].lat, trail[i].lon);
				if (i === 0) {
					ctx.moveTo(x * dpr, y * dpr);
				} else {
					ctx.lineTo(x * dpr, y * dpr);
				}
			}
			ctx.stroke();
			ctx.globalAlpha = 1.0;
			ctx.restore();
		}

		// Draw all flights
		for (const flightId in flights) {
			const f = flights[flightId];
			if (typeof f.lat !== "number" || typeof f.lon !== "number") continue;
			const { x, y } = latLonToXY(f.lat, f.lon);

			// Draw the airplane as an SVG icon, rotated to 'track'
			const iconWidth = 20 * dpr;
			const aspect = planeImg && planeImg.naturalWidth && planeImg.naturalHeight
				? planeImg.naturalWidth / planeImg.naturalHeight
				: 1.0;
			const iconHeight = iconWidth / aspect;
			const angle = ((f.track ?? 0) - 90) * Math.PI / 180; // Convert to radians, rotate so 0 is up

			ctx.save();
			ctx.translate(x * dpr, y * dpr);
			ctx.rotate(angle);

			// Only draw the icon if loaded
			if (
				planeImg &&
				planeImg.complete &&
				planeImg.naturalWidth > 0 &&
				planeImg.naturalHeight > 0
			) {
				ctx.drawImage(
					planeImg,
					-iconWidth / 2,
					-iconHeight / 2,
					iconWidth,
					iconHeight
				);
			} else {
				// fallback: draw a gray triangle
				ctx.beginPath();
				ctx.moveTo(iconWidth / 2, 0);
				ctx.lineTo(-iconWidth * 0.3, iconHeight * 0.3);
				ctx.lineTo(-iconWidth * 0.3, -iconHeight * 0.3);
				ctx.closePath();
				ctx.fillStyle = "#888";
				ctx.fill();
			}

			ctx.restore();

			// Draw flightId
			ctx.save();
			ctx.font = `bold ${20 * dpr}px sans-serif`;
			ctx.fillStyle = "#222";
			ctx.textAlign = "center";
			ctx.textBaseline = "bottom";
			ctx.fillText(f.flightId, x * dpr, (y - 32) * dpr);
		}
	}

	function connectWS() {
		// Only connect if running in the browser
		if (typeof window === 'undefined') return;
		const ws = new WebSocket("ws://localhost:8765");
		ws.onmessage = (event) => {
			try {
				const data = JSON.parse(event.data);
				if (data.flightId) {
					flights[data.flightId] = data;

					// Update trail
					if (!trails[data.flightId]) {
						trails[data.flightId] = [];
					}
					// Only add if position changed
					const trail = trails[data.flightId];
					if (
						trail.length === 0 ||
						trail[trail.length - 1].lat !== data.lat ||
						trail[trail.length - 1].lon !== data.lon
					) {
						trail.push({ lat: data.lat, lon: data.lon });
						// Limit trail length
						if (trail.length > 60) trail.shift();
					}

					drawFlights();
				}
			} catch (e) {
				console.error("Invalid WS data", e);
			}
		};
		ws.onopen = () => {
			console.log("WebSocket connected");
		};
		ws.onclose = () => {
			console.log("WebSocket closed, retrying in 2s...");
			setTimeout(connectWS, 2000);
		};
		ws.onerror = (e) => {
			console.error("WebSocket error", e);
			ws.close();
		};
	}

	function resizeCanvas() {
		dpr = (typeof window !== 'undefined' && window.devicePixelRatio) ? window.devicePixelRatio : 1;
		canvas.width = CANVAS_WIDTH * dpr;
		canvas.height = CANVAS_HEIGHT * dpr;
		canvas.style.width = CANVAS_WIDTH + "px";
		canvas.style.height = CANVAS_HEIGHT + "px";
		ctx = canvas.getContext("2d");
		drawFlights();
	}

	onMount(() => {
		// Only run this code in the browser
		if (typeof window === 'undefined') return;

		planeImg = new window.Image();
		planeImg.src = '/flight.svg';
		mapImg = new window.Image();
		mapImg.src = '/map.svg';

		planeImg.onload = () => {
			drawFlights();
		};
		mapImg.onload = () => {
			drawFlights();
		};
		resizeCanvas();
		connectWS();
	});

	// Redraw on window resize
	function handleResize() {
		resizeCanvas();
	}
</script>
<svelte:window on:resize={handleResize} />

<div class="flex flex-col items-center">
	<h1 class="text-3xl font-bold mb-4">Live Flight Map</h1>
	<canvas
		bind:this={canvas}
		width={CANVAS_WIDTH}
		height={CANVAS_HEIGHT}
		class="bg-base-300/50 p-5 rounded-xl"
		style="max-width: 100%; height: auto;"
	></canvas>
</div>
