<script lang="ts">
	// Progress Overview — circular ring of overall topic progress plus a
	// completed / in-progress / not-started breakdown. Theme-token driven so it
	// works in light and dark; the ring animates in once on mount (and is static
	// under prefers-reduced-motion via the global guard in app.css).
	import { onMount } from "svelte";
	import { Card } from "$lib/components/ui/card";
	import { Button } from "$lib/components/ui/button";

	let {
		completed = 0,
		inProgress = 0,
		notStarted = 0,
		total = 0,
		href = "/topics",
	}: {
		completed?: number;
		inProgress?: number;
		notStarted?: number;
		total?: number;
		href?: string;
	} = $props();

	const percent = $derived(
		total > 0 ? Math.round((completed / total) * 100) : 0,
	);

	// SVG ring geometry.
	const R = 52;
	const CIRC = 2 * Math.PI * R;

	// Animate the ring from empty → target after mount.
	let shown = $state(false);
	onMount(() => {
		const id = requestAnimationFrame(() => (shown = true));
		return () => cancelAnimationFrame(id);
	});
	const dashoffset = $derived(shown ? CIRC * (1 - percent / 100) : CIRC);

	const legend = $derived([
		{ label: "Completed", value: completed, color: "bg-primary" },
		{ label: "In progress", value: inProgress, color: "bg-emerald-400" },
		{
			label: "Not started",
			value: notStarted,
			color: "bg-muted-foreground/40",
		},
	]);
</script>

<Card class="glass-strong flex h-full flex-col gap-5 p-6">
	<div class="flex items-center justify-between gap-3">
		<div class="flex items-center gap-2.5">
			<div
				class="flex h-9 w-9 items-center justify-center rounded-xl bg-primary/10 text-primary"
			>
				<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" class="h-5 w-5" aria-hidden="true">
					<path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6" />
					<path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18" />
					<path d="M4 22h16" />
					<path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22" />
					<path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22" />
					<path d="M18 2H6v7a6 6 0 0 0 12 0V2Z" />
				</svg>
			</div>
			<div>
				<h3 class="font-title text-base font-bold text-foreground">Progress Overview</h3>
				<p class="text-xs text-muted-foreground">Across {total} topics</p>
			</div>
		</div>
	</div>

	<div class="flex items-center gap-6">
		<!-- Ring -->
		<div class="relative h-32 w-32 shrink-0">
			<svg class="h-full w-full -rotate-90" viewBox="0 0 120 120" aria-hidden="true">
				<circle cx="60" cy="60" r={R} fill="none" stroke="hsl(var(--muted))" stroke-width="10" />
				<circle
					cx="60"
					cy="60"
					r={R}
					fill="none"
					stroke="hsl(var(--primary))"
					stroke-width="10"
					stroke-linecap="round"
					stroke-dasharray={CIRC}
					stroke-dashoffset={dashoffset}
					style="transition: stroke-dashoffset 0.9s var(--ease-standard);"
				/>
			</svg>
			<div class="absolute inset-0 flex flex-col items-center justify-center">
				<span class="font-title text-3xl font-extrabold text-foreground">{percent}%</span>
				<span class="text-[11px] font-medium text-muted-foreground">complete</span>
			</div>
		</div>

		<!-- Legend -->
		<div class="flex min-w-0 flex-1 flex-col gap-3">
			{#each legend as item}
				<div class="flex items-center justify-between gap-2">
					<div class="flex items-center gap-2">
						<span class="h-2.5 w-2.5 rounded-full {item.color}"></span>
						<span class="text-sm text-muted-foreground">{item.label}</span>
					</div>
					<span class="font-title text-sm font-bold text-foreground">{item.value}</span>
				</div>
			{/each}
		</div>
	</div>

	<Button variant="outline" {href} class="w-full">View full analytics</Button>
</Card>
