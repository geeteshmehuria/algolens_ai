<script lang="ts">
	import { onMount, onDestroy } from 'svelte';

	let {
		onCancel = null
	} = $props<{
		onCancel?: (() => void) | null;
	}>();

	let step1Status = $state<'waiting' | 'running' | 'completed'>('running');
	let step2Status = $state<'waiting' | 'running' | 'completed'>('waiting');
	let step3Status = $state<'waiting' | 'running' | 'completed'>('waiting');

	let progressPercent = $state(5);
	let timer: any;

	onMount(() => {
		// Simulate progress milestones over a 45-second period
		let elapsed = 0;
		timer = setInterval(() => {
			elapsed += 1;
			
			// Update progress bar
			if (progressPercent < 95) {
				progressPercent += elapsed < 15 ? 2 : elapsed < 30 ? 1 : 0.5;
			}

			// Update steps status
			if (elapsed >= 12 && step1Status === 'running') {
				step1Status = 'completed';
				step2Status = 'running';
			}
			if (elapsed >= 26 && step2Status === 'running') {
				step2Status = 'completed';
				step3Status = 'running';
			}
			if (elapsed >= 42 && step3Status === 'running') {
				// hold at running until real promise resolves
			}
		}, 1000);
	});

	onDestroy(() => {
		if (timer) clearInterval(timer);
	});
</script>

<div class="flex flex-col items-center justify-center p-10 border border-slate-200 bg-white rounded-2xl shadow-sm max-w-[440px] w-full mx-auto my-12 gap-6">
	<!-- Spinner & Ring -->
	<div class="relative w-16 h-16 flex items-center justify-center">
		<div class="animate-spin rounded-full h-14 w-14 border-4 border-slate-100 border-t-blue-600"></div>
		<span class="absolute text-[10px] font-extrabold text-blue-600 font-mono">{Math.round(progressPercent)}%</span>
	</div>

	<div class="text-center flex flex-col gap-1">
		<h3 class="font-extrabold text-slate-800 text-sm">Generating AI Topic Notes</h3>
		<p class="text-[10px] text-slate-400 max-w-[280px] mx-auto leading-relaxed">
			This takes about 30–60 seconds. Notes are parsed and cached for all users once completed.
		</p>
	</div>

	<!-- Steps Checklist -->
	<div class="w-full flex flex-col gap-3.5 bg-slate-50 border border-slate-150 p-5 rounded-2xl">
		<!-- Step 1 -->
		<div class="flex items-center gap-3">
			<div class="w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold {step1Status === 'completed' ? 'bg-emerald-100 text-emerald-700' : step1Status === 'running' ? 'bg-blue-100 text-blue-700 animate-pulse' : 'bg-slate-200 text-slate-400'}">
				{step1Status === 'completed' ? '✓' : '1'}
			</div>
			<div class="flex flex-col">
				<span class="text-[11px] font-bold {step1Status === 'running' ? 'text-blue-900' : 'text-slate-600'}">Chunk A: Study Pack</span>
				<span class="text-[9px] text-slate-400">Core concepts, visual trace & roadmap</span>
			</div>
		</div>

		<!-- Step 2 -->
		<div class="flex items-center gap-3">
			<div class="w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold {step2Status === 'completed' ? 'bg-emerald-100 text-emerald-700' : step2Status === 'running' ? 'bg-blue-100 text-blue-700 animate-pulse' : 'bg-slate-200 text-slate-400'}">
				{step2Status === 'completed' ? '✓' : '2'}
			</div>
			<div class="flex flex-col">
				<span class="text-[11px] font-bold {step2Status === 'running' ? 'text-blue-900' : 'text-slate-600'}">Chunk B: Application Sandbox</span>
				<span class="text-[9px] text-slate-400">Practice questions, complexity tables & template scripts</span>
			</div>
		</div>

		<!-- Step 3 -->
		<div class="flex items-center gap-3">
			<div class="w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold {step3Status === 'completed' ? 'bg-emerald-100 text-emerald-700' : step3Status === 'running' ? 'bg-blue-100 text-blue-700 animate-pulse' : 'bg-slate-200 text-slate-400'}">
				{step3Status === 'completed' ? '✓' : '3'}
			</div>
			<div class="flex flex-col">
				<span class="text-[11px] font-bold {step3Status === 'running' ? 'text-blue-900' : 'text-slate-600'}">Chunk C: Last-Minute Revision</span>
				<span class="text-[9px] text-slate-400">Revision bullets & self-grading checklist</span>
			</div>
		</div>
	</div>

	{#if onCancel}
		<button
			onclick={onCancel}
			class="text-[10px] text-slate-400 hover:text-slate-600 underline font-semibold mt-1"
		>
			Cancel & Return
		</button>
	{/if}
</div>
