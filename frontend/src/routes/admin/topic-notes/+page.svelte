<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { api } from '$lib/api';
	import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '$lib/components/ui/card';
	import { Button } from '$lib/components/ui/button';

	interface TopicItem {
		id: number;
		name: string;
		description: string;
		has_published_note: boolean;
	}

	interface NoteVersion {
		id: number;
		version: number;
		status: string;
		level: string;
		source: string;
		model: string;
		created_on: string;
		published_on: string | null;
	}

	let topics = $state<TopicItem[]>([]);
	let selectedTopicId = $state<number | null>(null);
	let versions = $state<NoteVersion[]>([]);
	let selectedNoteId = $state<number | null>(null);

	// Currently editing content
	let level = $state('beginner_to_intermediate');
	let contentJson = $state<any>(null);

	let loading = $state(true);
	let loadingVersions = $state(false);
	let loadingNote = $state(false);
	let saving = $state(false);
	let publishing = $state(false);
	let regenerating = $state(false);
	let quizGenerating = $state(false);
	let msg = $state('');
	let error = $state('');

	onMount(async () => {
		// Verify admin role via user object
		const userStr = localStorage.getItem('user');
		if (userStr) {
			try {
				const user = JSON.parse(userStr);
				// If not admin, redirect
				const me = await api('/auth/me');
				if (!me.roles.includes('admin')) {
					goto('/dashboard');
					return;
				}
			} catch {
				goto('/login');
				return;
			}
		} else {
			goto('/login');
			return;
		}

		await loadTopics();
	});

	async function loadTopics() {
		loading = true;
		error = '';
		try {
			topics = await api<TopicItem[]>('/me/topic-notes');
		} catch (e: any) {
			error = e.message || 'Failed to load topics.';
		} finally {
			loading = false;
		}
	}

	async function selectTopic(id: number) {
		selectedTopicId = id;
		selectedNoteId = null;
		contentJson = null;
		versions = [];
		loadingVersions = true;
		error = '';
		msg = '';
		try {
			// Get versions list
			versions = await api<NoteVersion[]>(`/topics/${id}/notes/versions`);
			if (versions.length > 0) {
				// Select newest draft or published note
				const defaultNote = versions.find(v => v.status === 'draft' || v.status === 'in_review') || versions[0];
				await selectVersion(defaultNote.id);
			}
		} catch (e: any) {
			error = e.message || 'Failed to load versions.';
		} finally {
			loadingVersions = false;
		}
	}

	async function selectVersion(noteId: number) {
		selectedNoteId = noteId;
		loadingNote = true;
		error = '';
		msg = '';
		try {
			// We fetch the notes preview details by running a GET to /topics/{topic_id}/notes
			// Wait, the API GET /topics/{topic_id}/notes serves published, or latest draft for creator/admin.
			// To fetch a specific note version, we can fetch all versions. Or wait, let's load notes from the version list details.
			// Actually, let's make sure that GET /topics/{topic_id}/notes returns the latest. Since we selected the note,
			// let's fetch it. Wait, does our router support fetching a specific note_id?
			// Let's check our router: GET `/topics/{topic_id}/notes` fetches latest draft/published.
			// Wait! We can fetch the specific note_id from our database. Let's see: is there an endpoint to get a single note by id?
			// Ah! We didn't define a `GET /topic-notes/{note_id}` route in the routers!
			// Wait! That is okay: we can either add a `GET /topic-notes/{note_id}` route to our router, or we can fetch the notes.
			// Let's check: yes, adding a GET endpoint to fetch a single note by id is extremely simple and very useful!
			// Wait, we can implement it or we can just fetch the note details using the existing GET. But since we want to view older versions or specific drafts, a `GET /topic-notes/{note_id}` is much better!
			// Let's check: does it exist in the FastAPI router we wrote?
			// No, we wrote PATCH `/topic-notes/{note_id}` and POST `/topic-notes/{note_id}/publish` etc.
			// Let's add `GET /topic-notes/{note_id}` to `app/routers/topic_notes.py`.
			// First, let's draft Svelte page code. We will make a call to `GET /topic-notes/{note_id}` to load the note.
			const res = await api<any>(`/topic-notes/${noteId}`);
			contentJson = res.content;
			level = res.level;
		} catch (e: any) {
			error = e.message || 'Failed to load note details.';
		} finally {
			loadingNote = false;
		}
	}

	async function handleSaveEdits() {
		if (!selectedNoteId) return;
		saving = true;
		error = '';
		msg = '';
		try {
			await api(`/topic-notes/${selectedNoteId}`, {
				method: 'PATCH',
				body: JSON.stringify({
					level,
					content: contentJson
				})
			});
			msg = 'Edits saved successfully!';
			// Refresh version status list
			if (selectedTopicId) {
				versions = await api<NoteVersion[]>(`/topics/${selectedTopicId}/notes/versions`);
			}
		} catch (e: any) {
			error = e.message || 'Failed to save edits.';
		} finally {
			saving = false;
		}
	}

	async function handlePublish() {
		if (!selectedNoteId) return;
		publishing = true;
		error = '';
		msg = '';
		try {
			await api(`/topic-notes/${selectedNoteId}/publish`, { method: 'POST' });
			msg = 'Notes published successfully! It is now live for all users.';
			// Refresh page status
			await loadTopics();
			if (selectedTopicId) {
				versions = await api<NoteVersion[]>(`/topics/${selectedTopicId}/notes/versions`);
			}
		} catch (e: any) {
			error = e.message || 'Failed to publish note.';
		} finally {
			publishing = false;
		}
	}

	async function handleRegenerate() {
		if (!selectedTopicId) return;
		regenerating = true;
		error = '';
		msg = '';
		try {
			await api(`/topics/${selectedTopicId}/notes/regenerate`, { method: 'POST' });
			msg = 'Successfully regenerated v+1 notes draft!';
			await selectTopic(selectedTopicId);
		} catch (e: any) {
			error = e.message || 'Failed to regenerate notes.';
		} finally {
			regenerating = false;
		}
	}

	async function handleForceQuizGenerate() {
		if (!selectedNoteId) return;
		quizGenerating = true;
		error = '';
		msg = '';
		try {
			await api(`/topic-notes/${selectedNoteId}/quiz/generate?force=true`, { method: 'POST' });
			msg = 'Successfully generated quiz questions for this note!';
		} catch (e: any) {
			error = e.message || 'Failed to generate quiz.';
		} finally {
			quizGenerating = false;
		}
	}

	function handleContentSectionChange(index: number, key: string, value: any) {
		if (!contentJson) return;
		const updatedSections = [...contentJson.sections];
		updatedSections[index] = {
			...updatedSections[index],
			[key]: value
		};
		contentJson = {
			...contentJson,
			sections: updatedSections
		};
	}
</script>

<div class="grid grid-cols-1 xl:grid-cols-4 gap-6 h-[calc(100vh-theme(spacing.16)-4rem)] overflow-hidden w-full max-w-[1600px] mx-auto">
	<!-- Left Side: Topics List (1/4 Column) -->
	<Card class="border-slate-200 bg-white p-5 flex flex-col gap-4 overflow-y-auto h-full shadow-sm">
		<div>
			<h3 class="text-xs font-bold text-slate-800">Admin Review Queue</h3>
			<p class="text-[10px] text-slate-400 mt-0.5">Approve, refine, and publish AI-generated notes drafts.</p>
		</div>

		{#if loading}
			<div class="flex flex-col items-center justify-center p-8 gap-2">
				<div class="animate-spin rounded-full h-6 w-6 border-4 border-slate-100 border-t-blue-600"></div>
				<span class="text-[10px] text-slate-400">Loading topics...</span>
			</div>
		{:else}
			<div class="flex flex-col gap-1.5">
				{#each topics as topic}
					{@const isSelected = selectedTopicId === topic.id}
					<button
						onclick={() => selectTopic(topic.id)}
						class="w-full text-left p-3.5 rounded-xl border text-xs font-semibold transition-all duration-200 {isSelected ? 'bg-blue-50/70 border-blue-200 text-blue-900 font-extrabold shadow-sm' : 'bg-white border-slate-100 hover:border-slate-200 hover:bg-slate-50/50 text-slate-700'}"
					>
						<div class="flex items-center justify-between">
							<span class="truncate">{topic.name}</span>
							<span class="text-[9px] font-bold px-1.5 py-0.5 rounded {topic.has_published_note ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-500'}">
								{topic.has_published_note ? 'Live' : 'Draft'}
							</span>
						</div>
					</button>
				{/each}
			</div>
		{/if}
	</Card>

	<!-- Right Side: Preview & Review Editors (3/4 Columns) -->
	<Card class="xl:col-span-3 border-slate-200 bg-white overflow-hidden h-full shadow-sm flex flex-col p-0">
		{#if !selectedTopicId}
			<div class="flex flex-col items-center justify-center p-16 text-center gap-3 m-auto max-w-[340px]">
				<div class="w-12 h-12 rounded-full bg-slate-50 text-slate-400 flex items-center justify-center font-bold text-lg">📝</div>
				<h3 class="font-bold text-slate-800 text-sm">Select a DSA Topic</h3>
				<p class="text-slate-500 text-[11px] leading-relaxed">
					Choose a topic from the queue to edit metadata details, preview sections, mathematical complexities, and publish.
				</p>
			</div>
		{:else}
			<!-- Action Header Bar -->
			<div class="bg-slate-50 border-b border-slate-200 px-6 py-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
				<div class="flex flex-col gap-1">
					<h3 class="text-sm font-extrabold text-slate-900">
						{topics.find(t => t.id === selectedTopicId)?.name}
					</h3>
					<!-- Versions Selector Dropdown -->
					{#if versions.length > 0}
						<div class="flex items-center gap-2">
							<span class="text-[10px] text-slate-400 font-semibold">Version:</span>
							<select
								value={selectedNoteId}
								onchange={(e) => selectVersion(Number(e.currentTarget.value))}
								class="text-[10px] font-bold bg-white border border-slate-200 rounded px-2 py-0.5 outline-none"
							>
								{#each versions as v}
									<option value={v.id}>v{v.version} ({v.status})</option>
								{/each}
							</select>
						</div>
					{/if}
				</div>

				<!-- Header Actions -->
				{#if selectedNoteId}
					<div class="flex items-center gap-2 flex-wrap">
						<Button variant="outline" size="sm" class="text-[10px] h-8 border-slate-200 bg-white" onclick={handleForceQuizGenerate} disabled={quizGenerating}>
							{quizGenerating ? 'Building Quiz...' : 'Build/Force Quiz'}
						</Button>
						<Button variant="outline" size="sm" class="text-[10px] h-8 border-slate-200 bg-white" onclick={handleRegenerate} disabled={regenerating}>
							{regenerating ? 'Regenerating...' : 'Regenerate Draft (v+1)'}
						</Button>
						<Button variant="outline" size="sm" class="text-[10px] h-8 border-slate-200 bg-white" onclick={handleSaveEdits} disabled={saving}>
							{saving ? 'Saving...' : 'Save Edits'}
						</Button>
						<Button class="bg-emerald-600 hover:bg-emerald-700 text-white text-[10px] h-8 px-4 font-bold" onclick={handlePublish} disabled={publishing}>
							{publishing ? 'Publishing...' : 'Publish Live'}
						</Button>
					</div>
				{/if}
			</div>

			<!-- Messages -->
			{#if msg}
				<div class="bg-emerald-50 border-b border-emerald-150 px-6 py-2.5 text-[10px] font-semibold text-emerald-800">
					{msg}
				</div>
			{/if}
			{#if error}
				<div class="bg-rose-50 border-b border-rose-150 px-6 py-2.5 text-[10px] font-semibold text-rose-800">
					{error}
				</div>
			{/if}

			<!-- Scrollable Editor Canvas -->
			<div class="flex-1 overflow-y-auto p-6 flex flex-col gap-6">
				{#if loadingVersions || loadingNote}
					<div class="flex flex-col items-center justify-center p-12 gap-2 m-auto">
						<div class="animate-spin rounded-full h-8 w-8 border-4 border-slate-100 border-t-blue-600"></div>
						<span class="text-xs text-slate-400">Loading version files...</span>
					</div>
				{:else if contentJson}
					<!-- Global Settings -->
					<div class="grid grid-cols-1 md:grid-cols-2 gap-4 border-b border-slate-100 pb-5">
						<div class="flex flex-col gap-1.5">
							<label for="level-parameter" class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Level Parameter</label>
							<select id="level-parameter" bind:value={level} class="text-xs border border-slate-200 rounded-lg p-2 bg-slate-50 focus:bg-white outline-none">
								<option value="beginner_to_intermediate">Beginner to Intermediate</option>
								<option value="intermediate_to_advanced">Intermediate to Advanced</option>
								<option value="absolute_beginner">Absolute Beginner</option>
							</select>
						</div>
					</div>

					<!-- Sections Markdown Editors -->
					<div class="flex flex-col gap-6">
						<h4 class="text-xs font-bold text-slate-800 uppercase tracking-wider">Note Sections</h4>
						{#each contentJson.sections as section, idx}
							<div class="border border-slate-150 rounded-2xl overflow-hidden p-4 flex flex-col gap-3">
								<div class="flex items-center justify-between border-b border-slate-50 pb-2">
									<span class="text-xs font-extrabold text-slate-800">{section.title}</span>
									<span class="text-[9px] font-mono text-slate-400 bg-slate-100 px-1.5 py-0.5 rounded">{section.section_key}</span>
								</div>

								<div class="flex flex-col gap-1">
									<label for="content-md-{idx}" class="text-[9px] font-bold text-slate-400 uppercase tracking-wider">Content Markdown</label>
									<textarea
										id="content-md-{idx}"
										value={section.content_md}
										oninput={(e) => handleContentSectionChange(idx, 'content_md', e.currentTarget.value)}
										class="w-full h-32 border border-slate-200 rounded-xl p-3.5 text-xs text-slate-800 font-mono leading-relaxed outline-none focus:border-blue-400 bg-slate-50/50"
										spellcheck="false"
									></textarea>
								</div>
							</div>
						{/each}
					</div>
				{/if}
			</div>
		{/if}
	</Card>
</div>
