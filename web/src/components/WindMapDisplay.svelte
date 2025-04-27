<script lang="ts">
    export let normalUrl: string | null;
    export let augmentedUrl: string | null;
    export let showMode: 'normal' | 'augmented';
    export let isLoading: boolean;
</script>

<div class="relative rounded-lg">
    {#if isLoading}
        <div class="absolute inset-0 flex items-center justify-center">
            <span class="loading loading-spinner loading-lg"></span>
        </div>
    {:else}
        <figure class="diff aspect-16/9" tabindex="-1">
            <div class="diff-item-1" role="img" tabindex="-1">
                <img alt="Normal wind map" src={normalUrl} />
            </div>
            <div class="diff-item-2" role="img">
                <img alt="Augmented wind map" src={augmentedUrl} />
            </div>
            <div class="diff-resizer"></div>
        </figure>
    {/if}
</div>