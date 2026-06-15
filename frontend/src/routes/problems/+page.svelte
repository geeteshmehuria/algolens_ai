<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { api } from '$lib/api';
	import { getToken } from '$lib/auth';
	import { loadMasterData } from '$lib/stores/common';
	import { Card, CardContent } from '$lib/components/ui/card';
	import { Input } from '$lib/components/ui/input';
	import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '$lib/components/ui/table';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import IllustratedPageHero from '$lib/components/layout/illustrated-page-hero.svelte';

	interface Problem {
		id: number;
		title: string;
		difficulty: string;
		topic_id: number;
		pattern_id: number;
		leetcode_url?: string;
	}

	interface Topic {
		id: number;
		name: string;
	}

	let problems = $state<Problem[]>([]);
	let topics = $state<Topic[]>([]);
	let filteredProblems = $state<Problem[]>([]);

	// Seed the topic filter from ?topic= so dashboard deep-links land pre-filtered.
	let selectedTopic = $state(page.url.searchParams.get('topic') ?? '');
	let selectedDifficulty = $state('');
	let searchQuery = $state('');
	let loading = $state(true);

	onMount(async () => {
		if (!getToken()) {
			goto('/login');
			return;
		}

		try {
			// Topics come from the cached master-data store (shared across pages),
			// so navigating back here doesn't refetch the dropdown list.
			const [probs, master] = await Promise.all([
				api<Problem[]>('/problems'),
				loadMasterData(['topics'])
			]);
			problems = probs;
			topics = (master.topics ?? []) as Topic[];

			applyFilters();
		} catch (e) {
			console.error('Failed to load problems metadata', e);
		} finally {
			loading = false;
		}
	});

	function applyFilters() {
		filteredProblems = problems.filter(p => {
			const matchesSearch = p.title.toLowerCase().includes(searchQuery.toLowerCase());
			const matchesTopic = selectedTopic === '' || p.topic_id === parseInt(selectedTopic);
			const matchesDifficulty = selectedDifficulty === '' || p.difficulty === selectedDifficulty;
			return matchesSearch && matchesTopic && matchesDifficulty;
		});
	}

	$effect(() => {
		searchQuery;
		selectedTopic;
		selectedDifficulty;
		if (problems.length > 0) {
			applyFilters();
		}
	});
</script>

<div class="flex flex-col gap-6">
	<!-- Illustrated hero with search + filters -->
	<IllustratedPageHero
		variant="problems"
		eyebrow="Practice"
		title="Practice Problems"
		subtitle="Sharpen your DSA skills with curated, interview-ready problems."
	>
		{#snippet controls()}
			<div class="flex w-full flex-col gap-1.5 sm:w-64">
				<label for="search" class="text-xs font-semibold text-muted-foreground">Search problem</label>
				<Input type="text" id="search" bind:value={searchQuery} placeholder="Search by title..." class="h-10 border-input bg-card" />
			</div>

			<div class="flex w-full flex-col gap-1.5 sm:w-48">
				<label for="topic" class="text-xs font-semibold text-muted-foreground">Topic</label>
				<select id="topic" class="h-10 cursor-pointer rounded-lg border border-input bg-card px-3 text-sm text-foreground transition-all focus:border-primary focus:outline-none focus:ring-2 focus:ring-ring/25" bind:value={selectedTopic}>
					<option value="">All Topics</option>
					{#each topics as topic}
						<option value={topic.id.toString()}>{topic.name}</option>
					{/each}
				</select>
			</div>

			<div class="flex w-full flex-col gap-1.5 sm:w-40">
				<label for="difficulty" class="text-xs font-semibold text-muted-foreground">Difficulty</label>
				<select id="difficulty" class="h-10 cursor-pointer rounded-lg border border-input bg-card px-3 text-sm text-foreground transition-all focus:border-primary focus:outline-none focus:ring-2 focus:ring-ring/25" bind:value={selectedDifficulty}>
					<option value="">All Difficulties</option>
					<option value="Easy">Easy</option>
					<option value="Medium">Medium</option>
					<option value="Hard">Hard</option>
				</select>
			</div>
		{/snippet}
	</IllustratedPageHero>

	<!-- Problems Table -->
	<Card class="border-border bg-card overflow-hidden p-0">
		{#if loading}
			<div class="flex flex-col items-center justify-center p-12 gap-3">
				<div class="animate-spin rounded-full h-8 w-8 border-4 border-border border-t-primary"></div>
				<p class="text-sm text-muted-foreground font-medium">Loading problems...</p>
			</div>
		{:else if filteredProblems.length === 0}
			<div class="flex flex-col items-center justify-center p-16 text-center gap-1.5">
				<h3 class="text-base font-bold text-foreground">No problems found</h3>
				<p class="text-xs text-muted-foreground max-w-[320px]">Try adjusting your search queries or filter selections.</p>
			</div>
		{:else}
			<div class="w-full overflow-x-auto">
				<Table>
					<TableHeader class="bg-muted/50">
						<TableRow class="hover:bg-transparent border-border">
							<TableHead class="font-bold text-muted-foreground pl-6 h-12">Title</TableHead>
							<TableHead class="font-bold text-muted-foreground h-12">Topic</TableHead>
							<TableHead class="font-bold text-muted-foreground h-12">Difficulty</TableHead>
							<TableHead class="font-bold text-muted-foreground h-12">LeetCode Link</TableHead>
							<TableHead class="font-bold text-muted-foreground pr-6 h-12 text-right">Actions</TableHead>
						</TableRow>
					</TableHeader>
					<TableBody>
						{#each filteredProblems as problem}
							{@const diffBorder = problem.difficulty === 'Easy' ? 'border-l-emerald-400' : problem.difficulty === 'Medium' ? 'border-l-amber-400' : 'border-l-rose-400'}
							<TableRow class="border-border hover:bg-accent transition-all">
								<TableCell class="border-l-[3px] {diffBorder} font-bold text-foreground pl-6 py-4">{problem.title}</TableCell>
								<TableCell class="py-4">
									<span class="text-xs font-semibold text-muted-foreground bg-muted px-2.5 py-1 rounded-full">
										{topics.find(t => t.id === problem.topic_id)?.name || 'General'}
									</span>
								</TableCell>
								<TableCell class="py-4">
									<Badge class="text-xs font-bold py-0.5 rounded-full {problem.difficulty === 'Easy' ? 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100 border-emerald-200' : problem.difficulty === 'Medium' ? 'bg-amber-50 text-amber-700 hover:bg-amber-100 border-amber-200' : 'bg-rose-50 text-rose-700 hover:bg-rose-100 border-rose-200'}">
										{problem.difficulty}
									</Badge>
								</TableCell>
								<TableCell class="py-4">
									{#if problem.leetcode_url}
										<a href={problem.leetcode_url} target="_blank" rel="noopener noreferrer" class="text-xs text-primary hover:text-primary/80 font-medium hover:underline">
											View URL ↗
										</a>
									{:else}
										<span class="text-xs text-muted-foreground">—</span>
									{/if}
								</TableCell>
								<TableCell class="pr-6 py-4 text-right">
									<Button class="text-xs h-8 px-4" href="/problems/{problem.id}">
										Learn & Practice
									</Button>
								</TableCell>
							</TableRow>
						{/each}
					</TableBody>
				</Table>
			</div>
		{/if}
	</Card>
</div>
