<script lang="ts">
	interface TopicItem {
		id: number;
		name: string;
		description: string;
		has_published_note: boolean;
		state?: {
			status: string;
			is_bookmarked: boolean;
			completed_sections_count: number;
			last_read_on: string | null;
		} | null;
		last_quiz?: {
			score: number;
			total: number;
		} | null;
	}

	let {
		topics = [],
		selectedTopicId = null,
		onSelectTopic
	} = $props<{
		topics: TopicItem[];
		selectedTopicId: number | null;
		onSelectTopic: (id: number) => void;
	}>();

	let searchQuery = $state('');
	let statusFilter = $state<'all' | 'in_progress' | 'completed' | 'bookmarked'>('all');

	// Filtering logic
	let filteredTopics = $derived(
		topics.filter((topic: TopicItem) => {
			const matchesSearch = topic.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
				(topic.description || '').toLowerCase().includes(searchQuery.toLowerCase());

			if (!matchesSearch) return false;

			const state = topic.state;
			if (statusFilter === 'in_progress') {
				return !!(state && state.status === 'reading');
			}
			if (statusFilter === 'completed') {
				return !!(state && (state.status === 'completed' || state.status === 'revised'));
			}
			if (statusFilter === 'bookmarked') {
				return !!(state && state.is_bookmarked);
			}
			return true;
		})
	);
</script>

<div class="flex flex-col h-full bg-white border-r border-slate-200 p-4 gap-4 w-80">
	<div class="flex flex-col gap-2">
		<h2 class="text-sm font-bold text-slate-800">Topics & Notes</h2>
		<input
			type="text"
			placeholder="Search topics..."
			bind:value={searchQuery}
			class="w-full text-xs px-3 py-2 border border-slate-200 rounded-lg bg-slate-50 focus:bg-white focus:outline-none focus:ring-1 focus:ring-blue-500 transition-all"
		/>
	</div>

	<!-- Status Filter Chips -->
	<div class="flex flex-wrap gap-1.5 border-b border-slate-100 pb-3">
		{#each [
			{ id: 'all', label: 'All' },
			{ id: 'in_progress', label: 'In Progress' },
			{ id: 'completed', label: 'Completed' },
			{ id: 'bookmarked', label: 'Bookmarked' }
		] as filter}
			<button
				onclick={() => statusFilter = filter.id as any}
				class="text-[10px] font-semibold px-2.5 py-1 rounded-full border transition-all duration-200 {statusFilter === filter.id ? 'bg-blue-600 text-white border-blue-600 shadow-sm' : 'bg-white text-slate-500 border-slate-200 hover:bg-slate-50 hover:text-slate-700'}"
			>
				{filter.label}
			</button>
		{/each}
	</div>

	<!-- List of Topics -->
	<div class="flex-1 overflow-y-auto flex flex-col gap-1 pr-1">
		{#if filteredTopics.length === 0}
			<div class="flex flex-col items-center justify-center p-8 text-center text-slate-400 gap-1">
				<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-8 h-8 opacity-60">
					<path stroke-linecap="round" stroke-linejoin="round" d="M12 9v6m3-3H9m12 0a9 9 0 11-18 0 9 9 0 0118 0z" />
				</svg>
				<span class="text-[11px] font-medium">No topics match filters</span>
			</div>
		{:else}
			{#each filteredTopics as topic}
				{@const isSelected = selectedTopicId === topic.id}
				{@const hasState = topic.state !== null && topic.state !== undefined}
				{@const isCompleted = hasState && (topic.state?.status === 'completed' || topic.state?.status === 'revised')}
				{@const isReading = hasState && topic.state?.status === 'reading'}
				{@const isBookmarked = hasState && topic.state?.is_bookmarked}

				<button
					onclick={() => onSelectTopic(topic.id)}
					class="w-full text-left p-3 rounded-xl border transition-all duration-200 {isSelected ? 'bg-blue-50/70 border-blue-200 shadow-sm text-blue-900 font-semibold' : 'bg-white border-slate-100 hover:border-slate-200 hover:bg-slate-50/50 text-slate-700'}"
				>
					<div class="flex items-start justify-between gap-2">
						<div class="flex flex-col gap-0.5 overflow-hidden">
							<span class="text-xs font-bold truncate">{topic.name}</span>
							<span class="text-[10px] text-slate-400 truncate font-medium">{topic.description || 'DSA Topic'}</span>
						</div>

						<div class="flex items-center gap-1">
							{#if isBookmarked}
								<span class="text-xs">⭐</span>
							{/if}
							{#if isCompleted}
								<span class="w-2.5 h-2.5 rounded-full bg-emerald-500" title="Completed"></span>
							{:else if isReading}
								<span class="w-2.5 h-2.5 rounded-full bg-blue-500 animate-pulse" title="Reading"></span>
							{/if}
						</div>
					</div>

					<div class="flex items-center justify-between mt-2.5 pt-2 border-t border-slate-50 text-[9px] text-slate-400 font-semibold">
						<div class="flex items-center gap-1.5">
							{#if topic.has_published_note}
								<span class="text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded">Notes Available</span>
							{:else}
								<span class="text-slate-400 bg-slate-100 px-1.5 py-0.5 rounded">AI Draft Only</span>
							{/if}
						</div>

						{#if topic.last_quiz}
							<span class="text-slate-500 font-bold bg-slate-50 px-1.5 py-0.5 rounded">
								Quiz: {topic.last_quiz.score}/{topic.last_quiz.total}
							</span>
						{/if}
					</div>
				</button>
			{/each}
		{/if}
	</div>
</div>
