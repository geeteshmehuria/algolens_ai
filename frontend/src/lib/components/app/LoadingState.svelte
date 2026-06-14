<script lang="ts">
	import { cn } from "$lib/utils";

	let {
		message = "Loading…",
		class: className = ""
	} = $props<{
		message?: string;
		class?: string;
	}>();
</script>

<div
	class={cn(
		"flex min-h-[280px] flex-col items-center justify-center gap-3 text-center",
		className
	)}
	role="status"
	aria-live="polite"
>
	<div
		class="h-8 w-8 animate-spin rounded-full border-4 border-slate-200 border-t-blue-600"
	></div>
	<p class="text-sm font-medium text-slate-500">{message}</p>
</div>
