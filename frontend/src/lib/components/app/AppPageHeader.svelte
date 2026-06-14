<script lang="ts">
	import type { Snippet } from "svelte";
	import { cn } from "$lib/utils";

	let {
		title,
		description = "",
		actions,
		class: className = ""
	} = $props<{
		title: string;
		description?: string;
		actions?: Snippet;
		class?: string;
	}>();
</script>

<div class={cn("flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between", className)}>
	<div class="min-w-0">
		<h1 class="font-title text-xl font-bold tracking-tight text-slate-900">{title}</h1>
		{#if description}
			<p class="mt-1 text-sm text-slate-500">{description}</p>
		{/if}
	</div>
	{#if actions}
		<div class="flex shrink-0 items-center gap-2">{@render actions()}</div>
	{/if}
</div>
