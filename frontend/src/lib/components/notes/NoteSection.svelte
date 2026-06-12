<script lang="ts">
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

	// Simple markdown parser helper
	function parseMarkdown(md: string): string {
		if (!md) return '';

		// Escape HTML tags slightly
		let html = md
			.replace(/&/g, '&amp;')
			.replace(/</g, '&lt;')
			.replace(/>/g, '&gt;');

		// Code blocks: ```language\ncode\n```
		html = html.replace(/```(?:[a-zA-Z0-9]+)?\n([\s\S]*?)\n```/g, '<pre class="bg-slate-900 text-slate-100 p-4 rounded-xl font-mono text-[12px] my-3 overflow-x-auto whitespace-pre">$1</pre>');

		// Inline code: `code`
		html = html.replace(/`([^`]+)`/g, '<code class="bg-slate-100 text-slate-700 px-1.5 py-0.5 rounded font-mono text-[11px] font-bold border border-slate-200/50">$1</code>');

		// Bold: **text**
		html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

		// Lists: - item
		html = html.replace(/^-\s+(.+)$/gm, '<li class="ml-4 list-disc pl-1 py-0.5 text-slate-600">$1</li>');

		// Wrap lists in ul
		html = html.replace(/((?:<li class="ml-4 list-disc pl-1 py-0.5 text-slate-600">.+<\/li>\n?)+)/g, '<ul class="my-3 flex flex-col gap-0.5">$1</ul>');

		// Line breaks
		html = html.replace(/\n\n/g, '</p><p class="my-3 text-slate-600 leading-relaxed text-xs">');

		return `<p class="text-slate-600 leading-relaxed text-xs">${html}</p>`;
	}

	let parsedContent = $derived(parseMarkdown(section.content_md));
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
					class="rounded border-slate-300 text-blue-600 focus:ring-blue-500 w-3.5 h-3.5 cursor-pointer"
				/>
				<span>Mark Read</span>
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
