<script lang="ts">
	import { cn } from "$lib/utils";

	type Day = { date: string; count: number };

	let { data = [], class: className = "" } = $props<{
		data?: Day[];
		class?: string;
	}>();

	// Pad the front so the first cell lands on its correct weekday row (Sun=0),
	// giving the GitHub-style column-per-week layout. Dates are UTC ISO strings.
	const cells = $derived.by<(Day | null)[]>(() => {
		if (!data.length) return [];
		const firstDow = new Date(data[0].date + "T00:00:00Z").getUTCDay();
		return [...Array.from({ length: firstDow }, () => null), ...data];
	});

	const total = $derived(data.reduce((s: number, d: Day) => s + d.count, 0));

	// Fixed emerald intensity buckets (avoids a color-only signal: each cell also
	// carries a title with the exact count for hover/screen-reader context).
	function level(count: number): string {
		if (count <= 0) return "bg-slate-100";
		if (count <= 2) return "bg-emerald-200";
		if (count <= 4) return "bg-emerald-400";
		if (count <= 6) return "bg-emerald-500";
		return "bg-emerald-600";
	}

	const fmt = (iso: string) =>
		new Date(iso + "T00:00:00Z").toLocaleDateString(undefined, {
			month: "short",
			day: "numeric",
			timeZone: "UTC"
		});
</script>

<div class={cn("flex flex-col gap-2", className)}>
	<div
		class="grid grid-flow-col grid-rows-[repeat(7,minmax(0,1fr))] gap-1"
		role="img"
		aria-label={`Activity over the last 12 weeks — ${total} attempts total`}
	>
		{#each cells as cell}
			{#if cell}
				<div
					class={cn("h-3 w-3 rounded-sm", level(cell.count))}
					title={`${fmt(cell.date)}: ${cell.count} attempt${cell.count === 1 ? "" : "s"}`}
				></div>
			{:else}
				<div class="h-3 w-3 rounded-sm bg-transparent"></div>
			{/if}
		{/each}
	</div>

	<div class="flex items-center gap-1.5 text-[10px] font-medium text-slate-400">
		<span>Less</span>
		<span class="h-3 w-3 rounded-sm bg-slate-100"></span>
		<span class="h-3 w-3 rounded-sm bg-emerald-200"></span>
		<span class="h-3 w-3 rounded-sm bg-emerald-400"></span>
		<span class="h-3 w-3 rounded-sm bg-emerald-500"></span>
		<span class="h-3 w-3 rounded-sm bg-emerald-600"></span>
		<span>More</span>
	</div>
</div>
