<script lang="ts">
	import { renderMarkdown } from '$lib/markdown';

	interface SectionData {
		section_key: string;
		title: string;
		content_md: string;
		examples?: string[];
		common_mistakes?: string[];
		interview_tips?: string[];
	}

	let {
		section,
		completed = false,
		onToggleComplete
	} = $props<{
		section: SectionData;
		completed: boolean;
		onToggleComplete: (completed: boolean) => void;
	}>();

	let isOpen = $state(true);

	// All note body content flows through the one shared, XSS-safe renderer
	// (headings, lists, bold/italic, code, and GFM tables).
	let parsedContent = $derived(renderMarkdown(section.content_md));
</script>

<div class="border border-slate-200 bg-white rounded-2xl overflow-hidden transition-all duration-200 shadow-sm {completed ? 'border-emerald-100 bg-emerald-50/5' : ''}">
	<!-- Header -->
	<div class="flex items-center justify-between px-6 py-4 bg-slate-50/50 border-b border-slate-100">
		<button onclick={() => isOpen = !isOpen} class="flex items-center gap-2.5 text-left flex-1 font-bold text-xs text-slate-800 hover:text-blue-600 transition-colors">
			<span class="text-[10px] text-slate-400 transform transition-transform duration-200 {isOpen ? 'rotate-90' : ''}">▶</span>
			<span>{section.title}</span>
		</button>

		<div class="flex items-center gap-3">
			{#if completed}
				<span class="text-[10px] font-bold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-100/50">Read ✓</span>
			{/if}
			<label class="flex items-center gap-1.5 cursor-pointer select-none text-[10px] font-semibold text-slate-500 hover:text-slate-800">
				<input
					type="checkbox"
					checked={completed}
					onchange={(e) => onToggleComplete(e.currentTarget.checked)}
					class="w-4 h-4 shrink-0 rounded border-slate-300 accent-blue-600 focus:ring-2 focus:ring-blue-500/40 cursor-pointer"
				/>
				<span class="leading-none">Mark Read</span>
			</label>
		</div>
	</div>

	<!-- Body -->
	{#if isOpen}
		<div class="p-6 flex flex-col gap-5">
			<div class="prose max-w-none text-slate-600">
				{@html parsedContent}
			</div>

			<!-- Examples -->
			{#if section.examples && section.examples.length > 0}
				<div class="flex flex-col gap-2">
					<h4 class="text-[11px] font-bold text-slate-800 uppercase tracking-wider">Examples</h4>
					<div class="flex flex-col gap-2">
						{#each section.examples as example}
							<div class="bg-slate-50 border border-slate-150 p-3.5 rounded-xl font-mono text-[11px] text-slate-700 whitespace-pre-wrap leading-relaxed">{example}</div>
						{/each}
					</div>
				</div>
			{/if}

			<!-- Common Mistakes -->
			{#if section.common_mistakes && section.common_mistakes.length > 0}
				<div class="bg-amber-50/40 border border-amber-200/55 rounded-2xl p-4 flex flex-col gap-2">
					<h4 class="text-[10px] font-extrabold text-amber-800 uppercase tracking-widest flex items-center gap-1.5">
						<span>⚠️</span> Common Mistakes
					</h4>
					<ul class="list-disc pl-5 text-[11.5px] text-amber-900/85 flex flex-col gap-1.5 leading-relaxed font-medium">
						{#each section.common_mistakes as mistake}
							<li>{mistake}</li>
						{/each}
					</ul>
				</div>
			{/if}

			<!-- Interview Tips -->
			{#if section.interview_tips && section.interview_tips.length > 0}
				<div class="bg-blue-50/35 border border-blue-200/40 rounded-2xl p-4 flex flex-col gap-2">
					<h4 class="text-[10px] font-extrabold text-blue-800 uppercase tracking-widest flex items-center gap-1.5">
						<span>💡</span> Interview Tips
					</h4>
					<ul class="list-disc pl-5 text-[11.5px] text-blue-900/85 flex flex-col gap-1.5 leading-relaxed font-medium">
						{#each section.interview_tips as tip}
							<li>{tip}</li>
						{/each}
					</ul>
				</div>
			{/if}
		</div>
	{/if}
</div>
