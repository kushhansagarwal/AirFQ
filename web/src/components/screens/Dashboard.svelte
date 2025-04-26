<script lang="ts">
  import { onMount } from 'svelte';
  
  let departureAirport = '';
  let arrivalAirport = '';
  let routeImage: string | null = null;
  let isLoading = false;
  let errorMessage = '';
  
  // Validation function for airport codes
  function isValidAirportCode(code: string): boolean {
    return /^K[A-Z]{3}$/.test(code);
  }
  
  // Function to fetch route image from dummy API
  async function fetchRouteImage() {
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
    routeImage = null;
    
    try {
      // Simulate API call with a timeout
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // This is a dummy API endpoint - in a real app, you would call your actual API
      // For demo purposes, we're generating a placeholder image URL
      const response = await fetch(`https://dummyapi.example/route?from=${departureAirport}&to=${arrivalAirport}`);
      
      if (!response.ok) {
        throw new Error('Failed to fetch route image');
      }
      
      // In a real implementation, you would get the image URL from the response
      // For this example, we'll use a placeholder image
      routeImage = `https://placehold.co/800x600/007bff/white?text=${departureAirport}+to+${arrivalAirport}`;
    } catch (error) {
      console.error('Error fetching route:', error);
      errorMessage = 'Failed to fetch route image. Please try again.';
    } finally {
      isLoading = false;
    }
  }
  
  // Reset the form
  function resetForm() {
    departureAirport = '';
    arrivalAirport = '';
    routeImage = null;
    errorMessage = '';
  }
</script>

<div class="flex flex-col gap-6">
  <h1 class="text-4xl font-bold">Flight Route Planner</h1>
  
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
        on:click={fetchRouteImage}
        disabled={!departureAirport || !arrivalAirport || isLoading || !isValidAirportCode(departureAirport) || !isValidAirportCode(arrivalAirport)}
      >
        {#if isLoading}
          <span class="loading loading-spinner"></span>
          Loading...
        {:else}
          Show Route
        {/if}
      </button>
    </div>
  </div>
  
  {#if errorMessage}
    <div class="alert alert-error">
      <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <span>{errorMessage}</span>
    </div>
  {/if}
  
  {#if routeImage}
    <div class="card bg-base-100 shadow-xl">
      <figure>
        <img src={routeImage} alt="Flight route from {departureAirport} to {arrivalAirport}" class="w-full" />
      </figure>
      <div class="card-body">
        <h2 class="card-title">Flight Route: {departureAirport} to {arrivalAirport}</h2>
        <p>This is a visualization of your selected flight route.</p>
        <div class="card-actions justify-end">
          <button class="btn btn-secondary" on:click={resetForm}>New Search</button>
        </div>
      </div>
    </div>
  {/if}
</div>
