<script lang="ts">
	import { onMount } from "svelte";
	import { goto } from "$app/navigation";
	import { api } from "$lib/api";
	import {
		Card,
		CardContent,
		CardHeader,
		CardTitle,
		CardDescription,
	} from "$lib/components/ui/card";
	import { Button } from "$lib/components/ui/button";

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

	let topics = $state<TopicItem[]>([]);
	let loading = $state(true);

	let searchQuery = $state("");
	let filterType = $state<"all" | "in_progress" | "completed" | "bookmarked">(
		"all",
	);

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

	// Filter and search topics
	let filteredTopics = $derived(
		topics.filter((topic) => {
			const matchesSearch =
				topic.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
				(topic.description || "")
					.toLowerCase()
					.includes(searchQuery.toLowerCase());

			if (!matchesSearch) return false;

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
</script>

<div class="flex flex-col gap-6 w-full">
	<!-- Top Summary Banner -->
	<Card
		class="border-slate-200 bg-white p-6 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4"
	>
		<CardHeader class="p-0 flex-1 min-w-0">
			<CardTitle class="text-lg font-bold text-slate-900"
				>AI DSA Study Notes</CardTitle
			>
			<CardDescription class="text-xs text-slate-500">
				Access deep structured revision summaries, complexity
				derivations, and interactive quizzes for 22 DSA categories.
			</CardDescription>
		</CardHeader>

		<div class="flex gap-2 shrink-0 w-full md:w-auto">
			<input
				type="text"
				placeholder="Search topics..."
				bind:value={searchQuery}
				class="text-xs px-3 py-2 border border-slate-200 rounded-lg bg-slate-50 focus:bg-white focus:outline-none focus:ring-1 focus:ring-blue-500 w-full md:w-60 transition-all"
			/>
		</div>
	</Card>

	<!-- Filters Row -->
	<div class="flex items-center gap-2">
		{#each [{ id: "all", label: "All Topics" }, { id: "in_progress", label: "In Progress" }, { id: "completed", label: "Completed" }, { id: "bookmarked", label: "Bookmarked" }] as filter}
			<button
				onclick={() => (filterType = filter.id as any)}
				class="text-xs font-semibold px-4 py-2 rounded-xl border transition-all duration-200 {filterType ===
				filter.id
					? 'bg-blue-600 text-white border-blue-600 shadow-sm'
					: 'bg-white text-slate-500 border-slate-200 hover:bg-slate-50 hover:text-slate-700'}"
			>
				{filter.label}
			</button>
		{/each}
	</div>

	<!-- Topics Grid -->
	{#if loading}
		<div
			class="flex flex-col items-center justify-center p-16 gap-3 bg-white border border-slate-200 rounded-2xl"
		>
			<div
				class="animate-spin rounded-full h-8 w-8 border-4 border-slate-200 border-t-blue-600"
			></div>
			<p class="text-xs text-slate-500 font-medium">
				Loading topics list...
			</p>
		</div>
	{:else if filteredTopics.length === 0}
		<Card
			class="border-slate-200 bg-white p-16 text-center flex flex-col items-center justify-center gap-2"
		>
			<h3 class="text-base font-bold text-slate-800">No notes found</h3>
			<p class="text-xs text-slate-400 max-w-[320px]">
				Adjust your search query or filters. Open a topic card to
				trigger your first note generation.
			</p>
		</Card>
	{:else}
		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
			{#each filteredTopics as topic}
				{@const hasState =
					topic.state !== null && topic.state !== undefined}
				{@const isCompleted =
					hasState &&
					(topic.state?.status === "completed" ||
						topic.state?.status === "revised")}
				{@const isReading =
					hasState && topic.state?.status === "reading"}
				{@const isBookmarked = hasState && topic.state?.is_bookmarked}

				<Card
					class="border-slate-200 bg-white hover:border-blue-400 transition-all duration-200 shadow-sm hover:shadow-md flex flex-col overflow-hidden group"
				>
					<CardHeader
						class="p-5 flex flex-col gap-1.5 border-b border-slate-50"
					>
						<div class="flex justify-between items-start">
							<span
								class="text-[9px] font-extrabold uppercase px-2 py-0.5 rounded border {topic.has_published_note
									? 'bg-blue-50 text-blue-700 border-blue-100'
									: 'bg-slate-100 text-slate-500 border-slate-200'}"
							>
								{topic.has_published_note
									? "Notes Available"
									: "AI Draft Only"}
							</span>

							<div class="flex items-center gap-1.5">
								{#if isBookmarked}
									<span class="text-xs" title="Bookmarked"
										>⭐</span
									>
								{/if}
								{#if isCompleted}
									<span
										class="text-[9px] font-extrabold bg-emerald-50 text-emerald-700 border border-emerald-100 px-2 py-0.5 rounded-full"
										>Completed</span
									>
								{:else if isReading}
									<span
										class="text-[9px] font-extrabold bg-blue-50 text-blue-700 border border-blue-100 px-2 py-0.5 rounded-full"
										>In Progress</span
									>
								{/if}
							</div>
						</div>

						<h3
							class="text-[14px] font-extrabold text-slate-900 mt-1.5 group-hover:text-blue-600 transition-colors"
						>
							{topic.name}
						</h3>
						<p
							class="text-[11px] text-slate-400 font-medium line-clamp-2 leading-relaxed min-h-[32px]"
						>
							{topic.description ||
								"Category of data structures and algorithms"}
						</p>
					</CardHeader>

					<CardContent
						class="p-5 flex flex-col gap-4 flex-1 justify-between bg-slate-50/20"
					>
						<div
							class="flex items-center justify-between text-[10px] font-bold text-slate-500"
						>
							<div class="flex items-center gap-1">
								<span>Sections read:</span>
								<span class="text-slate-800"
									>{topic.state?.completed_sections_count ||
										0}</span
								>
							</div>

							{#if topic.last_quiz}
								<span
									class="bg-slate-100 text-slate-700 border border-slate-200 px-2 py-0.5 rounded"
								>
									Quiz Score: {topic.last_quiz.score}/{topic
										.last_quiz.total}
								</span>
							{/if}
						</div>

						<Button
							class="bg-blue-600 hover:bg-blue-700 text-white w-full text-xs h-9 font-semibold"
							href="/topics/{topic.id}/notes"
						>
							Open Study Notes
						</Button>
					</CardContent>
				</Card>
			{/each}
		</div>
	{/if}
</div>
