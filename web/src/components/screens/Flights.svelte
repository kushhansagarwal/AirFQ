<script>
	import Flight from '../common/Flight.svelte';

	const flights = [
		{
			flightId: 'N32169',
			departureAirport: 'KSFO',
			arrivalAirport: 'KJFK'
		},
		{
			flightId: 'N777VP',
			departureAirport: 'KSFO',
			arrivalAirport: 'KJFK'
		},
		{
			flightId: 'N400JW',
			departureAirport: 'KSFO',
			arrivalAirport: 'KJFK'
		}
	];
</script>

<div class="grid grid-cols-2 gap-4 xl:grid-cols-3">
	{#each flights as flightInfo}
		<Flight {flightInfo} />
	{/each}
</div>
