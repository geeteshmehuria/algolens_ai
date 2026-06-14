<script lang="ts" module>
	// Difficulty → calm tinted styles. A small dot gives a non-color-only cue
	// so the level is distinguishable without relying on hue alone (a11y).
	const STYLES: Record<string, { badge: string; dot: string }> = {
		easy: {
			badge: "bg-emerald-50 text-emerald-700 border-emerald-200",
			dot: "bg-emerald-500"
		},
		medium: {
			badge: "bg-amber-50 text-amber-700 border-amber-200",
			dot: "bg-amber-500"
		},
		hard: {
			badge: "bg-rose-50 text-rose-700 border-rose-200",
			dot: "bg-rose-500"
		}
	};
	const FALLBACK = {
		badge: "bg-slate-100 text-slate-600 border-slate-200",
		dot: "bg-slate-400"
	};
</script>

<script lang="ts">
	import { cn } from "$lib/utils";

	let { difficulty = "", class: className = "" } = $props<{
		difficulty?: string;
		class?: string;
	}>();

	const style = $derived(STYLES[difficulty?.toLowerCase()] ?? FALLBACK);
	const label = $derived(
		difficulty ? difficulty[0].toUpperCase() + difficulty.slice(1).toLowerCase() : "—"
	);
</script>

<span
	class={cn(
		"inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-semibold",
		style.badge,
		className
	)}
>
	<span class={cn("h-1.5 w-1.5 rounded-full", style.dot)} aria-hidden="true"></span>
	{label}
</span>
