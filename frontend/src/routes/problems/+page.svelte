<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { api } from '$lib/api';
	import { Card, CardContent } from '$lib/components/ui/card';
	import { Input } from '$lib/components/ui/input';
	import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '$lib/components/ui/table';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';

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

	let selectedTopic = $state('');
	let selectedDifficulty = $state('');
	let searchQuery = $state('');
	let loading = $state(true);

	onMount(async () => {
		const token = localStorage.getItem('token');
		if (!token) {
			goto('/login');
			return;
		}

		try {
			[problems, topics] = await Promise.all([
				api<Problem[]>('/problems'),
				api<Topic[]>('/topics')
			]);

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
	<!-- Filter controls -->
	<Card class="border-slate-200 bg-white p-5">
		<div class="grid grid-cols-1 md:grid-cols-3 gap-6 items-end">
			<div class="flex flex-col gap-1.5">
				<label for="search" class="text-xs font-semibold text-slate-500">Search Problem</label>
				<Input type="text" id="search" bind:value={searchQuery} placeholder="Search by title..." class="h-10 border-slate-200 bg-white" />
			</div>

			<div class="flex flex-col gap-1.5">
				<label for="topic" class="text-xs font-semibold text-slate-500">Topic</label>
				<select id="topic" class="h-10 border border-slate-200 rounded-lg px-3 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all cursor-pointer text-slate-800" bind:value={selectedTopic}>
					<option value="">All Topics</option>
					{#each topics as topic}
						<option value={topic.id.toString()}>{topic.name}</option>
					{/each}
				</select>
			</div>

			<div class="flex flex-col gap-1.5">
				<label for="difficulty" class="text-xs font-semibold text-slate-500">Difficulty</label>
				<select id="difficulty" class="h-10 border border-slate-200 rounded-lg px-3 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all cursor-pointer text-slate-800" bind:value={selectedDifficulty}>
					<option value="">All Difficulties</option>
					<option value="Easy">Easy</option>
					<option value="Medium">Medium</option>
					<option value="Hard">Hard</option>
				</select>
			</div>
		</div>
	</Card>

	<!-- Problems Table -->
	<Card class="border-slate-200 bg-white overflow-hidden p-0">
		{#if loading}
			<div class="flex flex-col items-center justify-center p-12 gap-3">
				<div class="animate-spin rounded-full h-8 w-8 border-4 border-slate-200 border-t-blue-600"></div>
				<p class="text-sm text-slate-500 font-medium">Loading problems...</p>
			</div>
		{:else if filteredProblems.length === 0}
			<div class="flex flex-col items-center justify-center p-16 text-center gap-1.5">
				<h3 class="text-base font-bold text-slate-900">No problems found</h3>
				<p class="text-xs text-slate-500 max-w-[320px]">Try adjusting your search queries or filter selections.</p>
			</div>
		{:else}
			<div class="w-full overflow-x-auto">
				<Table>
					<TableHeader class="bg-slate-50">
						<TableRow class="hover:bg-transparent border-slate-200">
							<TableHead class="font-bold text-slate-600 pl-6 h-12">Title</TableHead>
							<TableHead class="font-bold text-slate-600 h-12">Topic</TableHead>
							<TableHead class="font-bold text-slate-600 h-12">Difficulty</TableHead>
							<TableHead class="font-bold text-slate-600 h-12">LeetCode Link</TableHead>
							<TableHead class="font-bold text-slate-600 pr-6 h-12 text-right">Actions</TableHead>
						</TableRow>
					</TableHeader>
					<TableBody>
						{#each filteredProblems as problem}
							<TableRow class="border-slate-200 hover:bg-slate-50/50 transition-all">
								<TableCell class="font-bold text-slate-900 pl-6 py-4">{problem.title}</TableCell>
								<TableCell class="py-4">
									<span class="text-xs font-semibold text-slate-600 bg-slate-100 px-2.5 py-1 rounded-full">
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
										<a href={problem.leetcode_url} target="_blank" rel="noopener noreferrer" class="text-xs text-blue-600 hover:text-blue-700 font-medium hover:underline">
											View URL ↗
										</a>
									{:else}
										<span class="text-xs text-slate-400">—</span>
									{/if}
								</TableCell>
								<TableCell class="pr-6 py-4 text-right">
									<Button class="bg-blue-600 hover:bg-blue-700 text-white text-xs h-8 px-4" href="/problems/{problem.id}">
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
