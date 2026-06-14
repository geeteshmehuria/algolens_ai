<script lang="ts" module>
	// Accent → tinted icon tile. Keeps stat cards on the shared palette
	// instead of each page hardcoding its own tile colors.
	const ACCENTS: Record<string, string> = {
		blue: "bg-blue-50 text-blue-600 border-blue-100",
		emerald: "bg-emerald-50 text-emerald-600 border-emerald-100",
		amber: "bg-amber-50 text-amber-600 border-amber-100",
		rose: "bg-rose-50 text-rose-600 border-rose-100",
		slate: "bg-slate-100 text-slate-600 border-slate-200"
	};
</script>

<script lang="ts">
	import { Card } from "$lib/components/ui/card";
	import { cn } from "$lib/utils";
	import type { Snippet } from "svelte";

	let {
		label,
		value,
		accent = "blue",
		valueClass = "",
		icon
	} = $props<{
		label: string;
		value: string | number;
		accent?: "blue" | "emerald" | "amber" | "rose" | "slate";
		valueClass?: string;
		icon?: Snippet;
	}>();
</script>

<Card class="flex items-center gap-4 border-slate-200 bg-white p-5">
	{#if icon}
		<div
			class={cn(
				"flex h-12 w-12 shrink-0 items-center justify-center rounded-xl border text-xl",
				ACCENTS[accent]
			)}
		>
			{@render icon()}
		</div>
	{/if}
	<div class="flex min-w-0 flex-col">
		<span class="text-xs font-medium text-slate-500">{label}</span>
		<span class={cn("font-title text-2xl font-bold text-slate-900", valueClass)}>{value}</span>
	</div>
</Card>
