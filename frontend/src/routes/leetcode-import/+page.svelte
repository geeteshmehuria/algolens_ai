<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { api } from '$lib/api';
	import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '$lib/components/ui/card';
	import { Input } from '$lib/components/ui/input';
	import { Label } from '$lib/components/ui/label';
	import { Button } from '$lib/components/ui/button';

	interface Topic {
		id: number;
		name: string;
	}

	interface Pattern {
		id: number;
		name: string;
		topic_id: number;
	}

	let topics = $state<Topic[]>([]);
	let patterns = $state<Pattern[]>([]);
	let filteredPatterns = $state<Pattern[]>([]);

	let leetcodeUrl = $state('');
	let selectedTopic = $state('');
	let selectedPattern = $state('');
	let selectedDifficulty = $state('Easy');

	let successMessage = $state('');
	let errorMessage = $state('');
	let isLoading = $state(false);

	onMount(async () => {
		if (!localStorage.getItem('token')) {
			goto('/login');
			return;
		}

		try {
			[topics, patterns] = await Promise.all([
				api<Topic[]>('/topics'),
				api<Pattern[]>('/patterns')
			]);
		} catch (e) {
			console.error(e);
		}
	});

	// Filter patterns based on selected topic
	$effect(() => {
		if (selectedTopic) {
			filteredPatterns = patterns.filter(p => p.topic_id === parseInt(selectedTopic));
		} else {
			filteredPatterns = [];
		}
		selectedPattern = '';
	});

	// Handle Submit
	async function handleImport(event: SubmitEvent) {
		event.preventDefault();
		errorMessage = '';
		successMessage = '';
		isLoading = true;

		try {
			const data = await api('/problems/import-leetcode-url', {
				method: 'POST',
				body: JSON.stringify({
					url: leetcodeUrl,
					topic_id: parseInt(selectedTopic),
					pattern_id: parseInt(selectedPattern),
					difficulty: selectedDifficulty
				})
			});

			successMessage = `Successfully imported "${data.title}"!`;
			leetcodeUrl = '';
			selectedTopic = '';
			selectedPattern = '';
		} catch (err: any) {
			errorMessage = err.message || 'Something went wrong.';
		} finally {
			isLoading = false;
		}
	}
</script>

<div class="flex flex-col gap-6 max-w-[800px] mx-auto w-full">
	<Card class="border-slate-200 bg-white p-6">
		<CardHeader class="p-0">
			<CardTitle class="text-lg font-bold text-slate-900">LeetCode Problem Importer</CardTitle>
			<CardDescription class="text-xs text-slate-500">
				Enter any LeetCode problem URL to index it locally. You can then trigger Gemini AI to create visualization steps and explanations.
			</CardDescription>
		</CardHeader>
	</Card>

	<Card class="border-slate-200 bg-white p-8">
		<form onsubmit={handleImport} class="flex flex-col gap-6">
			{#if errorMessage}
				<div class="bg-rose-50 border border-rose-100 text-rose-600 text-xs rounded-lg p-3.5 font-medium">
					{errorMessage}
				</div>
			{/if}
			{#if successMessage}
				<div class="bg-emerald-50 border border-emerald-100 text-emerald-600 text-xs rounded-lg p-3.5 font-medium">
					{successMessage}
				</div>
			{/if}

			<div class="flex flex-col gap-1.5">
				<Label for="url" class="text-slate-600">LeetCode Problem URL</Label>
				<Input type="url" id="url" bind:value={leetcodeUrl} required placeholder="https://leetcode.com/problems/two-sum/" class="h-10 border-slate-200 bg-white" />
			</div>

			<div class="grid grid-cols-1 md:grid-cols-3 gap-6">
				<div class="flex flex-col gap-1.5">
					<Label for="topic" class="text-slate-600">Topic Mapping</Label>
					<select id="topic" class="h-10 border border-slate-200 rounded-lg px-3 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all cursor-pointer text-slate-800" bind:value={selectedTopic} required>
						<option value="" disabled>Select Topic</option>
						{#each topics as topic}
							<option value={topic.id.toString()}>{topic.name}</option>
						{/each}
					</select>
				</div>

				<div class="flex flex-col gap-1.5">
					<Label for="pattern" class="text-slate-600">Pattern Mapping</Label>
					<select id="pattern" class="h-10 border border-slate-200 rounded-lg px-3 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all cursor-pointer text-slate-800 disabled:bg-slate-50 disabled:cursor-not-allowed" bind:value={selectedPattern} required disabled={!selectedTopic}>
						<option value="" disabled>Select Pattern</option>
						{#each filteredPatterns as pattern}
							<option value={pattern.id.toString()}>{pattern.name}</option>
						{/each}
					</select>
				</div>

				<div class="flex flex-col gap-1.5">
					<Label for="difficulty" class="text-slate-600">Assigned Difficulty</Label>
					<select id="difficulty" class="h-10 border border-slate-200 rounded-lg px-3 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all cursor-pointer text-slate-800" bind:value={selectedDifficulty} required>
						<option value="Easy">Easy</option>
						<option value="Medium">Medium</option>
						<option value="Hard">Hard</option>
					</select>
				</div>
			</div>

			<Button type="submit" class="w-fit h-10 px-6 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold" disabled={isLoading}>
				{#if isLoading}Importing...{:else}Import Problem{/if}
			</Button>
		</form>
	</Card>
</div>
