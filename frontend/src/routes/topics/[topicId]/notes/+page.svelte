<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { api } from '$lib/api';
	import { Card, CardContent } from '$lib/components/ui/card';
	import { Button } from '$lib/components/ui/button';

	// Components
	import NotesSidebar from '$lib/components/notes/NotesSidebar.svelte';
	import NoteSection from '$lib/components/notes/NoteSection.svelte';
	import CodeTemplate from '$lib/components/notes/CodeTemplate.svelte';
	import ComplexityTable from '$lib/components/notes/ComplexityTable.svelte';
	import TocPanel from '$lib/components/notes/TocPanel.svelte';
	import ChecklistPanel from '$lib/components/notes/ChecklistPanel.svelte';
	import QuizRunner from '$lib/components/notes/QuizRunner.svelte';
	import GenerationProgress from '$lib/components/notes/GenerationProgress.svelte';
	import RevisionView from '$lib/components/notes/RevisionView.svelte';

	interface TopicItem {
		id: number;
		name: string;
		description: string;
		has_published_note: boolean;
		state?: any;
		last_quiz?: any;
	}

	interface NoteDetails {
		id: number;
		topic_id: number;
		version: number;
		status: string;
		level: string;
		estimated_reading_minutes: number;
		content: {
			sections: any[];
			pseudocode_templates?: any[];
			code_templates?: any[];
			complexity_notes?: any;
			confidence_checklist?: any[];
		};
		source: string;
		model: string;
		is_preview?: boolean;
	}

	const topicId = $derived(parseInt(page.params.topicId || '0'));
	const activeView = $derived(page.url.searchParams.get('view') || 'notes');

	// Page State
	let topicsList = $state<TopicItem[]>([]);
	let noteDetails = $state<NoteDetails | null>(null);
	let userState = $state<any>(null);

	let loading = $state(true);
	let generating = $state(false);
	let canGenerate = $state(false);
	let error = $state('');

	let isSidebarOpen = $state(false); // Mobile sidebar drawer state

	onMount(async () => {
		if (!localStorage.getItem('token')) {
			goto('/login');
			return;
		}
		await Promise.all([loadTopicsSummary(), loadNoteData()]);
	});

	// Reactively reload note data when topicId changes
	$effect(() => {
		if (topicId) {
			loadNoteData();
		}
	});

	async function loadTopicsSummary() {
		try {
			topicsList = await api<TopicItem[]>('/me/topic-notes');
		} catch (e) {
			console.error('Failed to load topics summary', e);
		}
	}

	async function loadNoteData() {
		loading = true;
		error = '';
		noteDetails = null;
		canGenerate = false;
		try {
			const res = await api<any>(`/topics/${topicId}/notes`);
			if (res.can_generate) {
				canGenerate = true;
			} else {
				noteDetails = res.note;
				userState = res.state;
			}
		} catch (e: any) {
			error = e.message || 'Failed to fetch study notes.';
		} finally {
			loading = false;
		}
	}

	async function handleGenerateNotes() {
		generating = true;
		error = '';
		try {
			await api(`/topics/${topicId}/notes/generate`, { method: 'POST' });
			await Promise.all([loadTopicsSummary(), loadNoteData()]);
		} catch (e: any) {
			error = e.message || 'Failed to generate study notes.';
		} finally {
			generating = false;
		}
	}

	// Interactive Actions
	async function toggleBookmark() {
		if (!userState) return;
		try {
			const res = await api<{ is_bookmarked: boolean }>(`/topics/${topicId}/notes/bookmark`, { method: 'POST' });
			userState.is_bookmarked = res.is_bookmarked;
			await loadTopicsSummary();
		} catch (e) {
			console.error('Bookmark toggle failed', e);
		}
	}

	async function handleToggleSectionRead(key: string, completed: boolean) {
		if (!userState) return;
		try {
			const res = await api<any>(`/topics/${topicId}/notes/progress`, {
				method: 'PUT',
				body: JSON.stringify({ section_key: key, completed })
			});
			userState.completed_sections = res.completed_sections;
			await loadTopicsSummary();
		} catch (e) {
			console.error('Failed to update progress', e);
		}
	}

	async function handleToggleChecklist(key: string, checked: boolean) {
		if (!userState) return;
		try {
			const res = await api<any>(`/topics/${topicId}/notes/checklist`, {
				method: 'PUT',
				body: JSON.stringify({ key, checked })
			});
			userState.checklist_state = res.checklist_state;
		} catch (e) {
			console.error('Failed to update checklist', e);
		}
	}

	async function handleMarkTopicCompleted() {
		if (!userState) return;
		try {
			const res = await api<any>(`/topics/${topicId}/notes/progress`, {
				method: 'PUT',
				body: JSON.stringify({ status: 'completed' })
			});
			userState.status = res.status;
			await loadTopicsSummary();
			alert('Topic marked as Completed! Great job! 🎉');
		} catch (e) {
			console.error('Failed to complete topic', e);
		}
	}

	function navigateToTopic(id: number) {
		isSidebarOpen = false;
		goto(`/topics/${id}/notes?view=${activeView}`);
	}

	function setView(view: 'notes' | 'revision' | 'quiz') {
		goto(`/topics/${topicId}/notes?view=${view}`);
	}

	// Scroll into view helper for TOC
	function scrollToSection(key: string) {
		const el = document.getElementById(`section-${key}`);
		if (el) {
			el.scrollIntoView({ behavior: 'smooth', block: 'start' });
		}
	}

	// Derive current topic item
	let currentTopicItem = $derived(topicsList.find(t => t.id === topicId));
</script>

<div class="flex h-[calc(100vh-theme(spacing.16)-4rem)] gap-6 w-full max-w-[1500px] mx-auto overflow-hidden">
	<!-- Left Side: Collapsible Topics list (Desktop only) -->
	<div class="hidden xl:block h-full shrink-0">
		<NotesSidebar
			topics={topicsList}
			selectedTopicId={topicId}
			onSelectTopic={navigateToTopic}
		/>
	</div>

	<!-- Mobile Sidebar Drawer Overlay -->
	{#if isSidebarOpen}
		<div class="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 xl:hidden" onclick={() => isSidebarOpen = false}>
			<div class="absolute left-0 top-0 bottom-0 w-80 bg-white shadow-xl h-full flex flex-col" onclick={(e) => e.stopPropagation()}>
				<NotesSidebar
					topics={topicsList}
					selectedTopicId={topicId}
					onSelectTopic={navigateToTopic}
				/>
			</div>
		</div>
	{/if}

	<!-- Center Panel & Right Panel Wrapper -->
	<div class="flex-1 flex flex-col lg:flex-row gap-6 h-full overflow-hidden">
		<!-- Middle: Content Area (Scrolls) -->
		<div class="flex-1 flex flex-col h-full overflow-y-auto bg-slate-50/20 border border-slate-200/50 rounded-2xl p-6 gap-6 relative">
			<!-- Header Action bar -->
			<div class="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-100 pb-5">
				<div class="flex flex-col gap-1">
					<div class="flex items-center gap-3">
						<button
							onclick={() => isSidebarOpen = true}
							class="xl:hidden bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs py-1.5 px-3 rounded-lg border"
						>
							☰ Topics
						</button>

						<h2 class="text-base font-extrabold text-slate-900">
							{currentTopicItem?.name || 'Study Notes'}
						</h2>
					</div>
					{#if noteDetails}
						<span class="text-[10px] text-slate-400 font-semibold">
							Version {noteDetails.version} · {noteDetails.level.replace(/_/g, ' ')} · Estimated {noteDetails.estimated_reading_minutes} min read
						</span>
					{/if}
				</div>

				<div class="flex items-center gap-2">
					{#if noteDetails}
						<button
							onclick={toggleBookmark}
							class="bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 text-xs py-1.5 px-3 rounded-xl shadow-sm font-semibold flex items-center gap-1.5 transition-colors"
						>
							<span>{userState?.is_bookmarked ? '★ Bookmarked' : '☆ Bookmark'}</span>
						</button>
					{/if}

					<!-- View Mode Toggles -->
					<div class="flex bg-slate-100 p-1 rounded-xl border">
						<button
							onclick={() => setView('notes')}
							class="text-[11px] font-bold px-3 py-1.5 rounded-lg transition-all {activeView === 'notes' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-800'}"
						>
							Learn Notes
						</button>
						<button
							onclick={() => setView('revision')}
							class="text-[11px] font-bold px-3 py-1.5 rounded-lg transition-all {activeView === 'revision' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-800'}"
						>
							Revision
						</button>
						<button
							onclick={() => setView('quiz')}
							class="text-[11px] font-bold px-3 py-1.5 rounded-lg transition-all {activeView === 'quiz' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-800'}"
						>
							Quiz
						</button>
					</div>
				</div>
			</div>

			<!-- Main View Router -->
			{#if loading}
				<div class="flex flex-col items-center justify-center min-h-[300px] gap-3">
					<div class="animate-spin rounded-full h-8 w-8 border-4 border-slate-200 border-t-blue-600"></div>
					<p class="text-xs text-slate-500 font-medium">Opening study folder...</p>
				</div>
			{:else if error}
				<div class="bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-2xl p-5 leading-relaxed">
					<strong>Failed to load:</strong> {error}
				</div>
			{:else if generating}
				<GenerationProgress onCancel={() => generating = false} />
			{:else if canGenerate}
				<!-- Initial Generation Screen -->
				<div class="flex flex-col items-center justify-center text-center p-12 gap-5 max-w-[380px] m-auto">
					<div class="w-14 h-14 bg-blue-50 text-blue-600 rounded-full flex items-center justify-center text-xl font-bold">🧠</div>
					<div class="flex flex-col gap-1.5">
						<h3 class="font-extrabold text-slate-800 text-base">Generate AI DSA Study Notes</h3>
						<p class="text-xs text-slate-500 leading-relaxed">
							No study notes exist yet for <strong>{currentTopicItem?.name}</strong>. Google Gemini will build a highly-detailed revision sheet, code template scripts, and interactive quiz.
						</p>
					</div>
					<Button class="bg-blue-600 hover:bg-blue-700 text-white w-full h-10 text-xs font-semibold shadow" onclick={handleGenerateNotes}>
						Generate Topic Notes
					</Button>
				</div>
			{:else if noteDetails}
				{#if activeView === 'notes'}
					<!-- 1. Notes View Mode -->
					{#if noteDetails.is_preview}
						<div class="bg-amber-50 border border-amber-200 rounded-2xl p-4 text-[11px] font-semibold text-amber-800 flex items-center justify-between gap-3 leading-relaxed shadow-sm">
							<span>⚠️ Viewing Draft Version. Rendered live for admin review. Click publish to make visible for all users.</span>
							<Button class="bg-amber-600 hover:bg-amber-700 text-white text-[10px] h-7 px-3 font-semibold shrink-0" href="/admin/topic-notes">Review Queue</Button>
						</div>
					{/if}

					<div class="flex flex-col gap-6">
						{#each noteDetails.content.sections as section}
							{#if section.section_key !== 'revision_notes'}
								<div id="section-{section.section_key}">
									<NoteSection
										{section}
										completed={userState?.completed_sections.includes(section.section_key) || false}
										onToggleComplete={(checked) => handleToggleSectionRead(section.section_key, checked)}
									/>
								</div>
							{/if}
						{/each}

						<!-- Code Templates Section -->
						{#if noteDetails.content.code_templates && noteDetails.content.code_templates.length > 0}
							<div class="flex flex-col gap-3.5 pt-4">
								<h3 class="text-xs font-bold text-slate-800 uppercase tracking-wider">Core Implementations</h3>
								<div class="flex flex-col gap-5">
									{#each noteDetails.content.code_templates as template}
										<CodeTemplate {template} />
									{/each}
								</div>
							</div>
						{/if}

						<!-- Complexity Table Section -->
						{#if noteDetails.content.complexity_notes}
							<div class="pt-4">
								<ComplexityTable notes={noteDetails.content.complexity_notes} />
							</div>
						{/if}
					</div>
				{:else if activeView === 'revision'}
					<!-- 2. Revision View Mode -->
					<RevisionView
						data={{
							topic_name: currentTopicItem?.name || 'DSA Topic',
							level: noteDetails.level,
							revision_section: noteDetails.content.sections.find(s => s.section_key === 'revision_notes'),
							code_templates: noteDetails.content.code_templates || [],
							confidence_checklist: noteDetails.content.confidence_checklist || [],
							checklist_state: userState?.checklist_state || {}
						}}
						onToggleCheck={handleToggleChecklist}
						onMarkTopicCompleted={handleMarkTopicCompleted}
						topicCompleted={userState?.status === 'completed'}
					/>
				{:else if activeView === 'quiz'}
					<!-- 3. Quiz View Mode -->
					<QuizRunner
						noteId={noteDetails.id}
						onQuizCompleted={async () => {
							await loadTopicsSummary();
						}}
					/>
				{/if}
			{/if}
		</div>

		<!-- Right Side: TOC + Checklist (Desktop only - hidden in quiz/revision) -->
		{#if noteDetails && activeView === 'notes'}
			<div class="hidden lg:flex flex-col gap-6 w-80 shrink-0 h-full overflow-y-auto pr-1">
				<TocPanel
					sections={noteDetails.content.sections.filter(s => s.section_key !== 'revision_notes')}
					completedSections={userState?.completed_sections || []}
					onSelectSection={scrollToSection}
				/>

				{#if noteDetails.content.confidence_checklist}
					<ChecklistPanel
						items={noteDetails.content.confidence_checklist}
						state={userState?.checklist_state || {}}
						onToggleCheck={handleToggleChecklist}
						onMarkTopicCompleted={handleMarkTopicCompleted}
						topicCompleted={userState?.status === 'completed'}
					/>
				{/if}
			</div>
		{/if}
	</div>
</div>
