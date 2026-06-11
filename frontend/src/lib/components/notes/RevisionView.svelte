<script lang="ts">
	import NoteSection from './NoteSection.svelte';
	import CodeTemplate from './CodeTemplate.svelte';
	import ChecklistPanel from './ChecklistPanel.svelte';

	interface RevisionData {
		topic_name: string;
		level: string;
		revision_section: any;
		code_templates: any[];
		confidence_checklist: any[];
		checklist_state: Record<string, boolean>;
	}

	let {
		data,
		onToggleCheck,
		onMarkTopicCompleted,
		topicCompleted = false
	} = $props<{
		data: RevisionData;
		onToggleCheck: (key: string, checked: boolean) => void;
		onMarkTopicCompleted: () => void;
		topicCompleted: boolean;
	}>();

	function handlePrint() {
		window.print();
	}
</script>

<div class="flex flex-col gap-6 w-full print:bg-white print:text-black">
	<!-- Actions Bar -->
	<div class="flex items-center justify-between border-b border-slate-150 pb-4 print:hidden">
		<div>
			<h2 class="text-sm font-bold text-slate-800">Revision Mode</h2>
			<p class="text-[10px] text-slate-400">High-density outline optimized for rapid review before coding interviews.</p>
		</div>
		<button
			onclick={handlePrint}
			class="bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 hover:border-slate-350 text-[10px] font-bold py-2 px-3 rounded-lg shadow-sm flex items-center gap-1.5 transition-all"
		>
			<span>🖨️</span> Print Revision Pack
		</button>
	</div>

	<!-- Title (visible in print) -->
	<div class="hidden print:flex flex-col gap-1 border-b border-slate-300 pb-4 mb-6">
		<h1 class="text-xl font-bold">{data.topic_name} — Revision Study Pack</h1>
		<div class="flex gap-4 text-xs text-slate-500 font-semibold">
			<span>Level: {data.level}</span>
			<span>Platform: AlgoLens AI</span>
		</div>
	</div>

	<!-- 1. Revision Notes -->
	{#if data.revision_section}
		<NoteSection
			section={data.revision_section}
			completed={false}
			onToggleComplete={() => {}}
		/>
	{/if}

	<!-- 2. Code Templates -->
	{#if data.code_templates && data.code_templates.length > 0}
		<div class="flex flex-col gap-3">
			<h3 class="text-xs font-bold text-slate-800 uppercase tracking-wider print:text-black">Core Templates</h3>
			<div class="flex flex-col gap-4">
				{#each data.code_templates as template}
					<CodeTemplate {template} />
				{/each}
			</div>
		</div>
	{/if}

	<!-- 3. Checklist -->
	{#if data.confidence_checklist && data.confidence_checklist.length > 0}
		<div class="print:break-before-page">
			<ChecklistPanel
				items={data.confidence_checklist}
				state={data.checklist_state}
				{onToggleCheck}
				{onMarkTopicCompleted}
				{topicCompleted}
			/>
		</div>
	{/if}
</div>
