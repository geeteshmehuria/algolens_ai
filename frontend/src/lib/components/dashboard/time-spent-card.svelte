<script lang="ts">
	// Activity / time card — a compact 7-bar chart with a headline figure and a
	// week-over-week change badge. Generic (label + value per bar) so it can show
	// study time when time-tracking exists, or another real signal (e.g. daily
	// attempts) until then. Bars animate up on mount; reduced-motion safe.
	import { onMount } from "svelte";
	import { Card } from "$lib/components/ui/card";

	let {
		title = "Weekly Activity",
		subtitle = "",
		headline = "",
		changePercent = null,
		bars = [],
	}: {
		title?: string;
		subtitle?: string;
		headline?: string;
		changePercent?: number | null;
		bars?: { label: string; value: number }[];
	} = $props();

	const max = $derived(Math.max(1, ...bars.map((b) => b.value)));
	const bestIndex = $derived(
		bars.reduce((bi, b, i, arr) => (b.value > arr[bi].value ? i : bi), 0),
	);

	let shown = $state(false);
	onMount(() => {
		const id = requestAnimationFrame(() => (shown = true));
		return () => cancelAnimationFrame(id);
	});

	const changeUp = $derived((changePercent ?? 0) >= 0);
</script>

<Card class="glass-strong flex h-full flex-col gap-4 p-6">
	<div class="flex items-start justify-between gap-3">
		<div class="flex items-center gap-2.5">
			<div
				class="flex h-9 w-9 items-center justify-center rounded-xl bg-primary/10 text-primary"
			>
				<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" class="h-5 w-5" aria-hidden="true">
					<circle cx="12" cy="12" r="10" />
					<path d="M12 6v6l4 2" />
				</svg>
			</div>
			<div>
				<h3 class="font-title text-base font-bold text-foreground">{title}</h3>
				{#if subtitle}<p class="text-xs text-muted-foreground">{subtitle}</p>{/if}
			</div>
		</div>
		{#if changePercent !== null}
			<span
				class="inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-semibold {changeUp
					? 'border-emerald-200 bg-emerald-50 text-emerald-700'
					: 'border-amber-200 bg-amber-50 text-amber-700'}"
				title="vs last week"
			>
				<span aria-hidden="true">{changeUp ? "▲" : "▼"}</span>
				{changeUp ? "+" : ""}{changePercent}%
			</span>
		{/if}
	</div>

	{#if headline}
		<div class="flex items-baseline gap-2">
			<span class="font-title text-2xl font-extrabold text-foreground">{headline}</span>
			{#if changePercent !== null}
				<span class="text-xs text-muted-foreground">vs last week</span>
			{/if}
		</div>
	{/if}

	<!-- Bars -->
	<div class="flex flex-1 items-end justify-between gap-2 pt-1" style="min-height: 90px;">
		{#each bars as bar, i}
			{@const pct = Math.round((bar.value / max) * 100)}
			{@const best = i === bestIndex && bar.value > 0}
			<div class="flex flex-1 flex-col items-center gap-1.5">
				<div class="flex h-[80px] w-full items-end justify-center">
					<div
						class="w-full max-w-[16px] rounded-md {best
							? 'bg-primary'
							: 'bg-primary/35'}"
						style="height: {shown ? Math.max(pct, bar.value > 0 ? 8 : 3) : 0}%; transition: height 0.6s var(--ease-standard) {i *
							0.05}s;"
						title="{bar.label}: {bar.value}"
					></div>
				</div>
				<span class="text-[10px] font-medium {best ? 'text-foreground' : 'text-muted-foreground'}">{bar.label}</span>
			</div>
		{/each}
	</div>
</Card>
