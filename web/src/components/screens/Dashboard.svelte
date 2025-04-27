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
	let showMode: 'normal' | 'augmented' = 'normal';

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
			// Fetch normal wind data first
			const normalRes = await fetch(`${PUBLIC_PY_API}/wind-data`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					departure: departureAirport,
					arrival: arrivalAirport,
					level
				})
			});

			if (!normalRes.ok) {
				throw new Error('Failed to fetch normal wind data');
			}

			const normalData = await normalRes.json();

			// Then fetch augmented wind data
			const augmentedRes = await fetch(`${PUBLIC_PY_API}/wind-data-augmented`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					departure: departureAirport,
					arrival: arrivalAirport,
					level
				})
			});

			if (!augmentedRes.ok) {
				throw new Error('Failed to fetch augmented wind data');
			}

			const augmentedData = await augmentedRes.json();

			imageData = {
				...imageData,
				[level]: {
					normal: normalData.url || null,
					augmented: augmentedData.url || null
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

	<div class="h-full grid gap-4">
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
			<div class="flex">
				<!-- Left sidebar with route info and controls -->
				<div class="w-64 bg-base-200 p-4 rounded-l-xl flex flex-col gap-4">
					<!-- Route display -->
					<div class="flex flex-col gap-2">
						<h3 class="font-bold text-lg">Flight Route</h3>
						<div class="flex flex-col gap-1">
							<div class="flex items-center gap-2">
								<span class="font-semibold">From:</span>
								<div>
									<div class="font-bold">{departureAirport}</div>
									<div class="text-base-content/70 text-xs">{getAirportFullName(departureAirport)}</div>
								</div>
							</div>
							<div class="flex items-center gap-2">
								<span class="font-semibold">To:</span>
								<div>
									<div class="font-bold">{arrivalAirport}</div>
									<div class="text-base-content/70 text-xs">{getAirportFullName(arrivalAirport)}</div>
								</div>
							</div>
						</div>
					</div>

					<!-- Flight level tabs -->
					<div class="flex flex-col gap-2">
						<h3 class="font-bold text-lg">Flight Level</h3>
						<div class="tabs tabs-boxed flex flex-wrap">
							{#each levels as level, idx}
								<button
									class="tab {selectedLevelIdx === idx ? 'tab-active' : ''}"
									on:click={() => handleLevelChange(idx)}
								>
									FL {level}
								</button>
							{/each}
						</div>
					</div>

					<!-- Display mode selector -->
					<div class="flex flex-col gap-2">
						<h3 class="font-bold text-lg">View</h3>
						<div class="btn-group">
							<button
								class="btn {showMode === 'normal' ? 'btn-active' : ''}"
								on:click={() => (showMode = 'normal')}
							>
								Normal
							</button>
							<button
								class="btn {showMode === 'augmented' ? 'btn-active' : ''}"
								on:click={() => (showMode = 'augmented')}
							>
								Augmented
							</button>
						</div>
					</div>
				</div>

				<!-- Wind map display -->
				<div class="flex-1 bg-base-100 p-4 rounded-r-xl">
					<WindMapDisplay
						normalUrl={imageData[levels[selectedLevelIdx]]?.normal}
						augmentedUrl={imageData[levels[selectedLevelIdx]]?.augmented}
						showMode={showMode}
						isLoading={isLoading}
					/>
				</div>
			</div>
		{/if}
	</div>
</div>
