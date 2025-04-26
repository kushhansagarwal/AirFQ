<script lang="ts">
  let departureAirport = '';
  let arrivalAirport = '';
  let isLoading = false;
  let errorMessage = '';
  let selectedLevel: string = 'sfc';
  let svgData: Record<string, string | null> = {
    sfc: null,
    '030': null,
    '060': null,
    max: null
  };

  const levels = ['sfc', '030', '060', '090'];

  function isValidAirportCode(code: string): boolean {
    return /^[A-Z]{4}$/.test(code);
  }

  async function fetchWindSVG(level: string) {
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
    svgData[level] = null;

    try {
      const response = await fetch('http://127.0.0.1:3001/wind-data-augmented', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          departure: departureAirport,
          arrival: arrivalAirport,
          level
        })
      });

      if (!response.ok) {
        throw new Error('Failed to fetch wind data');
      }

      const svgText = await response.text();
      svgData = { ...svgData, [level]: svgText };
    } catch (error) {
      console.error('Error fetching wind data:', error);
      errorMessage = 'Failed to fetch wind data. Please try again.';
    } finally {
      isLoading = false;
    }
  }

  function handleShowPlot(level: string) {
    selectedLevel = level;
    if (!svgData[level]) {
      fetchWindSVG(level);
    }
  }

  function resetForm() {
    departureAirport = '';
    arrivalAirport = '';
    errorMessage = '';
    svgData = {
      sfc: null,
      '030': null,
      '060': null,
      max: null
    };
    selectedLevel = 'sfc';
  }
</script>

<div class="flex flex-col gap-6">
  <h1 class="text-4xl font-bold">Flight Route Wind Plot</h1>

  <div class="flex flex-col md:flex-row gap-4">
    <label class="form-control w-full max-w-xs">
      <span class="label-text">Departure Airport</span>
      <input 
        type="text" 
        bind:value={departureAirport} 
        placeholder="Enter airport code (e.g., KSFO)" 
        class="input input-bordered w-full max-w-xs {!isValidAirportCode(departureAirport) && departureAirport ? 'input-error' : ''}" 
        maxlength="4"
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
        class="input input-bordered w-full max-w-xs {!isValidAirportCode(arrivalAirport) && arrivalAirport ? 'input-error' : ''}" 
        maxlength="4"
      />
      {#if arrivalAirport && !isValidAirportCode(arrivalAirport)}
        <span class="label-text-alt text-error">Must be a 4-letter code starting with K</span>
      {/if}
    </label>
    <div class="form-control">
      <div class="opacity-0 h-6">
        <span>Submit</span>
      </div>
      <button 
        class="btn btn-primary"
        on:click={() => handleShowPlot(selectedLevel)}
        disabled={!departureAirport || !arrivalAirport || isLoading || !isValidAirportCode(departureAirport) || !isValidAirportCode(arrivalAirport)}
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

  <div class="join my-2">
    {#each levels as level}
      <button
        class="btn join-item {selectedLevel === level ? 'btn-active btn-primary' : ''}"
        disabled={!departureAirport || !arrivalAirport || isLoading || !isValidAirportCode(departureAirport) || !isValidAirportCode(arrivalAirport)}
        on:click={() => handleShowPlot(level)}
        type="button"
      >
        {level}
      </button>
    {/each}
  </div>

  {#if errorMessage}
    <div class="alert alert-error">
      <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <span>{errorMessage}</span>
    </div>
  {/if}

  {#if svgData[selectedLevel]}
    <div class="card bg-base-100 shadow-xl">
      <figure>
        {@html svgData[selectedLevel]}
      </figure>
      <div class="card-body">
        <h2 class="card-title">Wind Plot: {departureAirport} to {arrivalAirport} ({selectedLevel})</h2>
        <p>This is a wind plot for your selected route and flight level.</p>
        <div class="card-actions justify-end">
          <button class="btn btn-secondary" on:click={resetForm}>New Search</button>
        </div>
      </div>
    </div>
  {/if}
</div>
