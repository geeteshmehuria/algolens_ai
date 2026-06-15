<script lang="ts">
	// Accessible 3-way theme switch (Light / System / Dark). Icon-only by default
	// (with aria-labels + tooltips); pass showLabels for a fuller control.
	import { theme, setTheme, type Theme } from "$lib/stores/theme";

	let { class: className = "", showLabels = false }: {
		class?: string;
		showLabels?: boolean;
	} = $props();

	const options: { value: Theme; label: string }[] = [
		{ value: "light", label: "Light" },
		{ value: "system", label: "System" },
		{ value: "dark", label: "Dark" },
	];
</script>

<div
	role="group"
	aria-label="Color theme"
	class="inline-flex items-center gap-0.5 rounded-lg border border-border bg-muted/60 p-0.5 {className}"
>
	{#each options as opt}
		{@const active = $theme === opt.value}
		<button
			type="button"
			aria-label="{opt.label} theme"
			aria-pressed={active}
			title="{opt.label} theme"
			onclick={() => setTheme(opt.value)}
			class="inline-flex items-center justify-center gap-1.5 rounded-[7px] px-2 py-1.5 text-xs font-semibold transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/55 {active
				? 'bg-background text-foreground shadow-sm'
				: 'text-muted-foreground hover:text-foreground'}"
		>
			{#if opt.value === "light"}
				<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4" aria-hidden="true">
					<circle cx="12" cy="12" r="4" />
					<path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41" />
				</svg>
			{:else if opt.value === "system"}
				<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4" aria-hidden="true">
					<rect x="2" y="3" width="20" height="14" rx="2" />
					<path d="M8 21h8M12 17v4" />
				</svg>
			{:else}
				<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4" aria-hidden="true">
					<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
				</svg>
			{/if}
			{#if showLabels}
				<span>{opt.label}</span>
			{/if}
		</button>
	{/each}
</div>
