<script lang="ts">
	import type { Snippet } from "svelte";
	import { cn } from "$lib/utils";

	let {
		title,
		description = "",
		icon,
		action,
		class: className = ""
	} = $props<{
		title: string;
		description?: string;
		icon?: Snippet;
		action?: Snippet;
		class?: string;
	}>();
</script>

<div
	class={cn(
		"flex flex-col items-center justify-center gap-3 rounded-2xl border border-dashed border-slate-200 bg-white px-6 py-14 text-center",
		className
	)}
>
	{#if icon}
		<div
			class="flex h-12 w-12 items-center justify-center rounded-full bg-slate-50 text-slate-400 ring-1 ring-slate-100"
		>
			{@render icon()}
		</div>
	{/if}
	<h3 class="text-base font-bold text-slate-800">{title}</h3>
	{#if description}
		<p class="max-w-sm text-sm leading-relaxed text-slate-500">{description}</p>
	{/if}
	{#if action}
		<div class="mt-2">{@render action()}</div>
	{/if}
</div>
