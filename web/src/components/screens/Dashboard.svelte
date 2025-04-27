<script lang="ts">
	import { PUBLIC_PY_API } from '$env/static/public';
	import { onMount, afterUpdate } from 'svelte';
	import WindMapDisplay from '../../components/WindMapDisplay.svelte';

	let departureAirport = '';
	let arrivalAirport = '';
	let isLoading = false;
	let errorMessage = '';
	let selectedLevelIdx: number = 0;
	const levels = ['sfc', '030', '060', '090'];
	let isDone = false;

	// imageData[level] = { normal: string|null, augmented: string|null }
	let imageData: Record<string, { normal: string | null; augmented: string | null }> = {
		sfc: { normal: null, augmented: null },
		'030': { normal: null, augmented: null },
		'060': { normal: null, augmented: null },
		'090': { normal: null, augmented: null }
	};

	function isValidAirportCode(code: string): boolean {
		return /^[A-Z]{4}$/.test(code);
	}

	function getAirportFullName(code: string): string {
		const airports: Record<string, string> = {
			KSFO: 'San Francisco International Airport',
			KJFK: 'John F. Kennedy International Airport',
			KLAX: 'Los Angeles International Airport',
			KORD: "O'Hare International Airport",
			KATL: 'Hartsfield-Jackson Atlanta International Airport'
		};
		return airports[code] || code;
	}

	async function fetchWindImages(level: string) {
		if (!isValidAirportCode(departureAirport)) {
			errorMessage = 'Departure airport must be a 4-letter code starting with K';
			return;
		}
		if (!isValidAirportCode(arrivalAirport)) {
			errorMessage = 'Arrival airport must be a 4-letter code starting with K';
			return;
		}
		errorMessage = '';
		isLoading = true;
		imageData[level] = { normal: null, augmented: null };

		try {
			const [normalRes, augmentedRes] = await Promise.all([
				fetch(`${PUBLIC_PY_API}/wind-data`, {
					method: 'POST',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify({
						departure: departureAirport,
						arrival: arrivalAirport,
						level
					})
				}),
				fetch(`${PUBLIC_PY_API}/wind-data-augmented`, {
					method: 'POST',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify({
						departure: departureAirport,
						arrival: arrivalAirport,
						level
					})
				})
			]);

			if (!normalRes.ok || !augmentedRes.ok) {
				throw new Error('Failed to fetch wind data');
			}

			const [normalImage, augmentedImage] = await Promise.all([normalRes.text(), augmentedRes.text()]);

			imageData = {
				...imageData,
				[level]: {
					normal: normalImage,
					augmented: augmentedImage
				}
			};
			isDone = true;
		} catch (error) {
			console.error('Error fetching wind data:', error);
			errorMessage = 'Failed to fetch wind data. Please try again.';
		} finally {
			isLoading = false;
		}
	}

	function handleShowPlot() {
		const level = levels[selectedLevelIdx];
		if (!imageData[level].normal || !imageData[level].augmented) {
			fetchWindImages(level);
		} else {
			isDone = true;
		}
	}

	function resetForm() {
		departureAirport = '';
		arrivalAirport = '';
		errorMessage = '';
		imageData = {
			sfc: { normal: null, augmented: null },
			'030': { normal: null, augmented: null },
			'060': { normal: null, augmented: null },
			'090': { normal: null, augmented: null }
		};
		selectedLevelIdx = 0;
		isDone = false;
	}

	function handleLevelChange(idx: number) {
		selectedLevelIdx = idx;
		const level = levels[idx];
		if (!imageData[level].normal || !imageData[level].augmented) {
			fetchWindImages(level);
		}
	}
</script>

<div class="flex flex-col gap-6">
	<h1 class="text-4xl font-bold">Flight Route Wind Plot</h1>

	<div class="h-full">
		<div class="flex flex-col gap-4 md:flex-row">
			<label class="form-control w-full max-w-xs">
				<span class="label-text">Departure Airport</span>
				<input
					type="text"
					bind:value={departureAirport}
					placeholder="Enter airport code (e.g., KSFO)"
					class="input input-bordered w-full max-w-xs {!isValidAirportCode(departureAirport) &&
					departureAirport
						? 'input-error'
						: ''}"
					maxlength="4"
					disabled={isDone}
				/>
				{#if departureAirport && !isValidAirportCode(departureAirport)}
					<span class="label-text-alt text-error">Must be a 4-letter code starting with K</span>
				{/if}
			</label>

			<label class="form-control w-full max-w-xs">
				<span class="label-text">Arrival Airport</span>
				<input
					type="text"
					bind:value={arrivalAirport}
					placeholder="Enter airport code (e.g., KJFK)"
					class="input input-bordered w-full max-w-xs {!isValidAirportCode(arrivalAirport) &&
					arrivalAirport
						? 'input-error'
						: ''}"
					maxlength="4"
					disabled={isDone}
				/>
				{#if arrivalAirport && !isValidAirportCode(arrivalAirport)}
					<span class="label-text-alt text-error">Must be a 4-letter code starting with K</span>
				{/if}
			</label>
			<div class="form-control">
				<div class="h-6 opacity-0">
					<span>Submit</span>
				</div>
				<button
					class="btn btn-primary"
					on:click={handleShowPlot}
					disabled={!departureAirport ||
						!arrivalAirport ||
						isLoading ||
						!isValidAirportCode(departureAirport) ||
						!isValidAirportCode(arrivalAirport) ||
						isDone}
				>
					{#if isLoading}
						<span class="loading loading-spinner"></span>
						Loading...
					{:else}
						Show Wind Plot
					{/if}
				</button>
			</div>
		</div>

		{#if errorMessage}
			<div class="alert alert-error">
				<svg
					xmlns="http://www.w3.org/2000/svg"
					class="h-6 w-6 shrink-0 stroke-current"
					fill="none"
					viewBox="0 0 24 24"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"
					/>
				</svg>
				<span>{errorMessage}</span>
			</div>
		{/if}

		{#if isDone}
			<div class="card bg-base-100 shadow-xl">
				<!-- Route display at top -->
				<div class="bg-base-200 flex items-center justify-between rounded-t-xl p-4">
					<div class="w-32 text-center">
						<div class="text-2xl font-bold">{departureAirport}</div>
						<div class="text-base-content/70 text-xs">{getAirportFullName(departureAirport)}</div>
					</div>
					<div class="relative flex flex-1 flex-col items-center">
						<div
							class="bg-base-300 absolute top-1/2 left-0 h-1 w-full"
							style="transform: translateY(-50%);"
						></div>
						<div class="bg-base-200 z-10 px-2">
							<img src="/flight.svg" alt="Plane" width="40" height="40" />
						</div>
					</div>
					<div class="w-32 text-center">
						<div class="text-2xl font-bold">{arrivalAirport}</div>
						<div class="text-base-content/70 text-xs">{getAirportFullName(arrivalAirport)}</div>
					</div>
				</div>

				<WindMapDisplay 
					{levels}
					svgData={imageData}
					{isLoading}
					{selectedLevelIdx}
					on:levelChange={(e: CustomEvent<number>) => handleLevelChange(e.detail)} 
				/>

				<div class="card-body">
					<h2 class="card-title">
						Wind Plot: {departureAirport} to {arrivalAirport} (FL {levels[selectedLevelIdx]})
					</h2>
					<p>
						View wind patterns for your selected route and flight level.<br />
						Switch between normal and augmented views using the buttons above.
					</p>
					<div class="card-actions justify-end">
						<button class="btn btn-secondary" on:click={resetForm}>New Search</button>
					</div>
				</div>
			</div>
		{/if}
	</div>
</div>
