<script lang="ts">
	interface LineExplanation {
		lines: string;
		explanation: string;
	}

	interface CodeTemplateData {
		language: string;
		name: string;
		code: string;
		line_explanations?: LineExplanation[];
	}

	let {
		template
	} = $props<{
		template: CodeTemplateData;
	}>();

	let copied = $state(false);
	let selectedLineIndex = $state<number | null>(null);

	// Parse lines and helper to check for explanations
	let lines = $derived(template.code.split('\n'));

	function getExplanationForLine(lineNum: number): LineExplanation | null {
		if (!template.line_explanations) return null;
		for (const expl of template.line_explanations) {
			const ranges = expl.lines.split(',').map((r: string) => r.trim());
			for (const r of ranges) {
				if (r.includes('-')) {
					const [start, end] = r.split('-').map(Number);
					if (lineNum >= start && lineNum <= end) return expl;
				} else {
					if (Number(r) === lineNum) return expl;
				}
			}
		}
		return null;
	}

	async function copyCode() {
		try {
			await navigator.clipboard.writeText(template.code);
			copied = true;
			setTimeout(() => copied = false, 2000);
		} catch (e) {
			console.error('Failed to copy', e);
		}
	}
</script>

<div class="border border-slate-200 bg-slate-950 rounded-2xl overflow-hidden flex flex-col shadow-md">
	<!-- Header -->
	<div class="bg-slate-900 border-b border-slate-800 px-6 py-3 flex items-center justify-between text-xs">
		<div class="flex items-center gap-2">
			<span class="font-extrabold text-slate-300">{template.name}</span>
			<span class="text-[10px] font-bold text-slate-500 bg-slate-800 px-2 py-0.5 rounded-full uppercase tracking-wider">{template.language}</span>
		</div>

		<button
			onclick={copyCode}
			class="text-[10px] font-extrabold px-3 py-1.5 rounded-lg border border-slate-800 text-slate-400 hover:text-white hover:bg-slate-800 bg-transparent transition-all duration-200"
		>
			{copied ? 'Copied ✓' : 'Copy Code'}
		</button>
	</div>

	<!-- Content split into code layout & explanations -->
	<div class="grid grid-cols-1 md:grid-cols-5 divide-y md:divide-y-0 md:divide-x divide-slate-800 min-h-[220px]">
		<!-- Code box (60%) -->
		<div class="md:col-span-3 flex flex-col font-mono text-[12px] py-3 overflow-x-auto bg-slate-950 leading-relaxed max-w-full">
			{#each lines as line, index}
				{@const lineNum = index + 1}
				{@const explanation = getExplanationForLine(lineNum)}
				{@const hasExplanation = explanation !== null}
				{@const isSelected = selectedLineIndex === lineNum}

				<div
					onclick={() => { if (hasExplanation) selectedLineIndex = isSelected ? null : lineNum; }}
					class="flex py-0.5 w-full cursor-default select-none border-l-3 transition-colors {isSelected ? 'bg-blue-950/45 border-blue-500' : hasExplanation ? 'hover:bg-slate-900/60 border-slate-700/30' : 'border-transparent'}"
				>
					<span class="w-10 text-right pr-3.5 text-slate-600 font-bold text-[10px] select-none flex items-center justify-end gap-1">
						{#if hasExplanation}
							<span class="text-[9px] text-blue-400 hover:text-blue-300">ℹ</span>
						{/if}
						<span>{lineNum}</span>
					</span>
					<span class="text-slate-300 whitespace-pre">{line}</span>
				</div>
			{/each}
		</div>

		<!-- Explanation Panel (40%) -->
		<div class="md:col-span-2 p-5 bg-slate-900/40 text-xs flex flex-col gap-3 justify-center">
			<h4 class="text-[10px] font-extrabold text-slate-500 uppercase tracking-widest border-b border-slate-800/80 pb-2">Line Annotations</h4>

			{#if selectedLineIndex !== null}
				{@const expl = getExplanationForLine(selectedLineIndex)}
				{#if expl}
					<div class="flex flex-col gap-1.5 animate-fadeIn">
						<span class="font-extrabold text-blue-400 text-[11px]">Lines {expl.lines} Explanation:</span>
						<p class="text-slate-400 leading-relaxed text-xs">{expl.explanation}</p>
					</div>
				{/if}
			{:else}
				<div class="text-slate-500 leading-relaxed py-4 text-center">
					<p>Click any line marked with <strong>ℹ</strong> to view inline architectural comments and interview trade-offs.</p>
				</div>
			{/if}
		</div>
	</div>
</div>

<style>
	@keyframes -global-fadeIn {
		from { opacity: 0; transform: translateY(2px); }
		to { opacity: 1; transform: translateY(0); }
	}
	.animate-fadeIn {
		animation: fadeIn 0.18s ease-out forwards;
	}
</style>
