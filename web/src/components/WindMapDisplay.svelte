<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	export let levels: string[];
	export let svgData: Record<string, { normal: string | null; augmented: string | null }>;
	export let isLoading: boolean;
	export let selectedLevelIdx: number;

	let showMode: 'normal' | 'augmented' = 'normal';

	const dispatch = createEventDispatcher<{
		levelChange: number;
	}>();

	function handleLevelChange(idx: number) {
		dispatch('levelChange', idx);
	}
</script>

<div class="flex flex-col items-center gap-4 p-4">
	<!-- Flight level tabs -->
	<div class="tabs tabs-boxed">
		{#each levels as level, idx}
			<button
				class="tab {selectedLevelIdx === idx ? 'tab-active' : ''}"
				on:click={() => handleLevelChange(idx)}
			>
				FL {level}
			</button>
		{/each}
	</div>

	<!-- Display mode selector -->
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

	<!-- Image display container -->
	<div class="relative w-full rounded-lg ">
		{#if isLoading}
			<div class="absolute inset-0 flex items-center justify-center">
				<span class="loading loading-spinner loading-lg"></span>
			</div>
		{:else if showMode === 'normal' && svgData[levels[selectedLevelIdx]]?.normal}
			<div class="mx-auto flex items-center justify-center">
				<img src={svgData[levels[selectedLevelIdx]].normal} alt="Normal wind map" class="max-w-full" />
			</div>
		{:else if showMode === 'augmented' && svgData[levels[selectedLevelIdx]]?.augmented}
			<div class="mx-auto flex items-center justify-center">
				<img src={svgData[levels[selectedLevelIdx]].augmented} alt="Augmented wind map" class="max-w-full" />
			</div>
		{:else}
			<div class="absolute inset-0 flex items-center justify-center">
				<p>No data available for this view</p>
			</div>
		{/if}
	</div>
</div>
