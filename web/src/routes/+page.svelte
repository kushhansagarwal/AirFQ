<script lang="ts">
	import Nav from '../components/common/Nav.svelte';
	import Dashboard from '../components/screens/Dashboard.svelte';
	import Demo from '../components/screens/Demo.svelte';
	import Flights from '../components/screens/Flights.svelte';
	import LiveMap from '../components/screens/LiveMap.svelte';
	import { menuState } from '../utils/menuState.svelte';

	const menu = menuState();
</script>

<svelte:head>
	<title>AirFQ - Dashboard</title>
</svelte:head>

<div class="flex h-dvh flex-col">
	<Nav />
	<div class="flex flex-1">
		<!-- Vertical navigation on the left -->
		<div class="bg-base-100 w-64 shadow-md">
			<ul class="menu p-4 w-full gap-2">
				<li><button class={menu.selectedTab === 'Dashboard' ? 'active' : ''} onclick={() => (menu.selectedTab = 'Dashboard')}>Dashboard</button></li>
				<li><button class={menu.selectedTab === 'Flights' ? 'active' : ''} onclick={() => (menu.selectedTab = 'Flights')}>Flights</button></li>
				<li><button class={menu.selectedTab === 'Live Map' ? 'active' : ''} onclick={() => (menu.selectedTab = 'Live Map')}>Live Map</button></li>
				<li><button class={menu.selectedTab === 'Demo' ? 'active' : ''} onclick={() => (menu.selectedTab = 'Demo')}>Demo</button></li>
				<li><button class={menu.selectedTab === 'Settings' ? 'active' : ''} onclick={() => (menu.selectedTab = 'Settings')}>Settings</button></li>
			</ul>
		</div>
		<!-- Main content area that changes based on what's being displayed -->
		<main class="bg-base-200 flex-1 p-6">
			{#if menu.selectedTab === 'Dashboard'}
				<Dashboard />
			{:else if menu.selectedTab === 'Flights'}
				<Flights />
			{:else if menu.selectedTab === 'Demo'}
				<Demo />
			{:else if menu.selectedTab === 'Settings'}
				<h1 class="text-4xl font-bold">Settings</h1>
				<p class="mt-4 text-lg">Welcome to your settings</p>
			{:else if menu.selectedTab === 'Live Map'}
				<LiveMap />
			{/if}
		</main>
	</div>
</div>
