<script lang="ts">
	import { onMount } from "svelte";
	import { goto } from "$app/navigation";
	import { api } from "$lib/api";
	import { Card, CardContent, CardHeader } from "$lib/components/ui/card";
	import { Button } from "$lib/components/ui/button";
	import LoadingState from "$lib/components/app/LoadingState.svelte";
	import EmptyState from "$lib/components/app/EmptyState.svelte";
	import IllustratedPageHero from "$lib/components/layout/illustrated-page-hero.svelte";

	interface TopicItem {
		id: number;
		name: string;
		description: string;
		slug?: string | null;
		category?: string | null;
		difficulty?: string | null;
		learning_order?: number | null;
		estimated_time_minutes?: number | null;
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

	let topics = $state<TopicItem[]>([]);
	let loading = $state(true);

	let searchQuery = $state("");
	let filterType = $state<"all" | "in_progress" | "completed" | "bookmarked">(
		"all",
	);
	let categoryFilter = $state<string>("all");

	const UNCATEGORIZED = "Other";

	const difficultyStyles: Record<string, string> = {
		beginner: "border-emerald-100 bg-emerald-50 text-emerald-700",
		intermediate: "border-amber-100 bg-amber-50 text-amber-700",
		advanced: "border-rose-100 bg-rose-50 text-rose-700",
	};

	onMount(async () => {
		if (!localStorage.getItem("token")) {
			goto("/login");
			return;
		}
		await loadTopics();
	});

	async function loadTopics() {
		try {
			topics = await api<TopicItem[]>("/me/topic-notes");
		} catch (e) {
			console.error("Failed to load topic notes summary", e);
		} finally {
			loading = false;
		}
	}

	const filters = [
		{ id: "all", label: "All Topics" },
		{ id: "in_progress", label: "In Progress" },
		{ id: "completed", label: "Completed" },
		{ id: "bookmarked", label: "Bookmarked" },
	] as const;

	// Distinct categories in curriculum (learning_order) order for the dropdown.
	let categories = $derived.by(() => {
		const seen: string[] = [];
		for (const t of topics) {
			const cat = t.category || UNCATEGORIZED;
			if (!seen.includes(cat)) seen.push(cat);
		}
		return seen;
	});

	// Filter and search topics
	let filteredTopics = $derived(
		topics.filter((topic) => {
			const matchesSearch =
				topic.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
				(topic.description || "")
					.toLowerCase()
					.includes(searchQuery.toLowerCase()) ||
				(topic.category || "")
					.toLowerCase()
					.includes(searchQuery.toLowerCase());

			if (!matchesSearch) return false;

			if (
				categoryFilter !== "all" &&
				(topic.category || UNCATEGORIZED) !== categoryFilter
			) {
				return false;
			}

			const state = topic.state;
			if (filterType === "in_progress") {
				return !!(state && state.status === "reading");
			}
			if (filterType === "completed") {
				return !!(
					state &&
					(state.status === "completed" || state.status === "revised")
				);
			}
			if (filterType === "bookmarked") {
				return !!(state && state.is_bookmarked);
			}
			return true;
		}),
	);

	// Group the filtered topics by category, preserving learning_order.
	let groupedTopics = $derived.by(() => {
		const groups: { category: string; topics: TopicItem[] }[] = [];
		const index = new Map<string, TopicItem[]>();
		for (const t of filteredTopics) {
			const cat = t.category || UNCATEGORIZED;
			let bucket = index.get(cat);
			if (!bucket) {
				bucket = [];
				index.set(cat, bucket);
				groups.push({ category: cat, topics: bucket });
			}
			bucket.push(t);
		}
		return groups;
	});
</script>

<div class="flex w-full flex-col gap-6">
	<!-- Illustrated hero with search + category controls -->
	<IllustratedPageHero
		variant="notes"
		eyebrow="Study Notes"
		title="AI DSA Study Notes"
		subtitle="Smart, structured, and AI-generated notes to help you learn faster and remember better — across 25 DSA categories."
	>
		{#snippet controls()}
			<div class="relative w-full sm:w-72">
				<svg
					class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
					xmlns="http://www.w3.org/2000/svg"
					fill="none"
					viewBox="0 0 24 24"
					stroke="currentColor"
					stroke-width="2"
				>
					<path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-4.35-4.35M17 11a6 6 0 11-12 0 6 6 0 0112 0z" />
				</svg>
				<input
					type="text"
					placeholder="Search topics…"
					bind:value={searchQuery}
					aria-label="Search topics"
					class="w-full rounded-lg border border-input bg-card/80 py-2 pl-9 pr-3 text-sm text-foreground transition-all focus:border-primary focus:bg-card focus:outline-none focus:ring-2 focus:ring-ring/25"
				/>
			</div>
			<div class="w-full sm:w-auto">
				<label class="sr-only" for="category-filter">Filter by category</label>
				<select
					id="category-filter"
					bind:value={categoryFilter}
					class="h-[38px] w-full rounded-lg border border-input bg-card px-3 text-sm font-semibold text-muted-foreground transition-all focus:border-primary focus:outline-none focus:ring-2 focus:ring-ring/25 sm:w-auto"
				>
					<option value="all">All categories</option>
					{#each categories as cat}
						<option value={cat}>{cat}</option>
					{/each}
				</select>
			</div>
		{/snippet}
	</IllustratedPageHero>

	<!-- Filters Row -->
	<div class="flex flex-wrap items-center gap-2">
		{#each filters as filter}
			<button
				onclick={() => (filterType = filter.id)}
				aria-pressed={filterType === filter.id}
				class="rounded-lg border px-4 py-2 text-xs font-semibold transition-all duration-200 {filterType ===
				filter.id
					? 'border-primary bg-primary text-primary-foreground shadow-sm'
					: 'border-border bg-card text-muted-foreground hover:bg-muted hover:text-foreground'}"
			>
				{filter.label}
			</button>
		{/each}
	</div>

	<!-- Topics Grid -->
	{#if loading}
		<LoadingState message="Loading topics…" />
	{:else if filteredTopics.length === 0}
		<EmptyState
			title={searchQuery || filterType !== "all" ? "No matching topics" : "No notes yet"}
			description={searchQuery || filterType !== "all"
				? "Try a different search term or clear your filters."
				: "Open a topic to generate your first AI study note."}
		>
			{#snippet icon()}
				<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8" class="h-6 w-6">
					<path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
				</svg>
			{/snippet}
			{#snippet action()}
				{#if searchQuery || filterType !== "all"}
					<Button variant="outline" onclick={() => { searchQuery = ""; filterType = "all"; }}>Clear filters</Button>
				{/if}
			{/snippet}
		</EmptyState>
	{:else}
		{#each groupedTopics as group}
			<section class="flex flex-col gap-4">
				<div class="flex items-center gap-3">
					<h2 class="font-title text-base font-bold tracking-tight text-slate-800">
						{group.category}
					</h2>
					<span class="rounded-full border border-slate-200 bg-slate-100 px-2 py-0.5 text-[10px] font-bold text-slate-500">
						{group.topics.length}
					</span>
					<div class="h-px flex-1 bg-slate-100"></div>
				</div>

				<div class="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
					{#each group.topics as topic}
						{@const hasState = topic.state !== null && topic.state !== undefined}
						{@const isCompleted =
							hasState &&
							(topic.state?.status === "completed" ||
								topic.state?.status === "revised")}
						{@const isReading = hasState && topic.state?.status === "reading"}
						{@const isBookmarked = hasState && topic.state?.is_bookmarked}

						<Card
							class="lift group flex flex-col overflow-hidden border-slate-200 bg-white shadow-sm hover:border-blue-300 hover:shadow-md"
						>
							<CardHeader class="flex flex-col gap-1.5 border-b border-slate-100 p-5">
								<div class="flex items-start justify-between gap-2">
									<div class="flex flex-wrap items-center gap-1.5">
										<span
											class="rounded border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide {topic.has_published_note
												? 'border-blue-100 bg-blue-50 text-blue-700'
												: 'border-slate-200 bg-slate-100 text-slate-500'}"
										>
											{topic.has_published_note ? "Notes Available" : "AI Draft Only"}
										</span>
										{#if topic.difficulty}
											<span
												class="rounded border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide {difficultyStyles[
													topic.difficulty
												] || 'border-slate-200 bg-slate-100 text-slate-500'}"
											>
												{topic.difficulty}
											</span>
										{/if}
									</div>

									<div class="flex items-center gap-1.5">
										{#if isBookmarked}
											<span class="text-sm" title="Bookmarked" aria-label="Bookmarked">⭐</span>
										{/if}
										{#if isCompleted}
											<span class="rounded-full border border-emerald-100 bg-emerald-50 px-2 py-0.5 text-[10px] font-bold text-emerald-700">Completed</span>
										{:else if isReading}
											<span class="rounded-full border border-blue-100 bg-blue-50 px-2 py-0.5 text-[10px] font-bold text-blue-700">In Progress</span>
										{/if}
									</div>
								</div>

								<h3 class="mt-1.5 font-title text-base font-bold text-slate-900 transition-colors group-hover:text-blue-600">
									{topic.name}
								</h3>
								<p class="line-clamp-2 min-h-[36px] text-xs leading-relaxed text-slate-500">
									{topic.description || "Category of data structures and algorithms"}
								</p>
							</CardHeader>

							<CardContent class="flex flex-1 flex-col justify-between gap-4 bg-slate-50/30 p-5">
								<div class="flex items-center justify-between text-xs font-medium text-slate-500">
									<span>
										Sections read:
										<span class="font-bold text-slate-800">{topic.state?.completed_sections_count || 0}</span>
									</span>

									{#if topic.last_quiz}
										<span class="rounded border border-slate-200 bg-slate-100 px-2 py-0.5 font-semibold text-slate-700">
											Quiz: {topic.last_quiz.score}/{topic.last_quiz.total}
										</span>
									{:else if topic.estimated_time_minutes}
										<span class="rounded border border-slate-200 bg-slate-100 px-2 py-0.5 font-semibold text-slate-700">
											~{topic.estimated_time_minutes} min
										</span>
									{/if}
								</div>

								<Button
									class="h-9 w-full bg-blue-600 text-sm font-semibold text-white hover:bg-blue-700"
									href="/topics/{topic.id}/notes"
								>
									Open Study Notes
								</Button>
							</CardContent>
						</Card>
					{/each}
				</div>
			</section>
		{/each}
	{/if}
</div>
