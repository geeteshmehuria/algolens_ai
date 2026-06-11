<script lang="ts">
	interface SectionItem {
		section_key: string;
		title: string;
	}

	let {
		sections = [],
		completedSections = [],
		onSelectSection
	} = $props<{
		sections: SectionItem[];
		completedSections: string[];
		onSelectSection: (key: string) => void;
	}>();

	function isCompleted(key: string) {
		return completedSections.includes(key);
	}
</script>

<div class="border border-slate-200 bg-white rounded-2xl p-5 shadow-sm flex flex-col gap-4 sticky top-20">
	<h3 class="text-xs font-bold text-slate-800 border-b border-slate-100 pb-2">Table of Contents</h3>
	
	<nav class="flex flex-col gap-1">
		{#each sections as section}
			{@const done = isCompleted(section.section_key)}
			<button
				onclick={() => onSelectSection(section.section_key)}
				class="flex items-center justify-between text-left px-3 py-2 rounded-lg text-[11px] font-semibold transition-all duration-150 hover:bg-slate-50 text-slate-600 hover:text-blue-600"
			>
				<span class="truncate">{section.title}</span>
				{#if done}
					<span class="text-emerald-500 font-bold text-xs" title="Read">✓</span>
				{:else}
					<span class="w-1.5 h-1.5 rounded-full bg-slate-200" title="Unread"></span>
				{/if}
			</button>
		{/each}
	</nav>
</div>
