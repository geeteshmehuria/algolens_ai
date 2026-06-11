<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { api } from '$lib/api';
	import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '$lib/components/ui/card';
	import { Button } from '$lib/components/ui/button';

	interface Roadmap {
		id: number;
		title: string;
		roadmap_data: {
			title: string;
			days: Array<{
				day: number;
				focus: string;
				tasks: string[];
			}>;
		};
		created_on: string;
	}

	let roadmaps = $state<Roadmap[]>([]);
	let loading = $state(true);
	let isGenerating = $state(false);

	onMount(async () => {
		if (!localStorage.getItem('token')) {
			goto('/login');
			return;
		}
		await loadRoadmaps();
	});

	async function loadRoadmaps() {
		try {
			roadmaps = await api<Roadmap[]>('/roadmap');
		} catch (e) {
			console.error(e);
		} finally {
			loading = false;
		}
	}

	async function generateRoadmap() {
		isGenerating = true;
		try {
			await api('/roadmap/generate', { method: 'POST' });
			await loadRoadmaps();
		} catch (e) {
			console.error(e);
		} finally {
			isGenerating = false;
		}
	}
</script>

<div class="flex flex-col gap-6 max-w-[900px] mx-auto w-full">
	<Card class="border-slate-200 bg-white p-6">
		<div class="flex justify-between items-center flex-wrap gap-4">
			<div class="flex flex-col gap-1">
				<h2 class="text-lg font-bold text-slate-900">Personalized Study Roadmaps</h2>
				<p class="text-xs text-slate-500">
					Gemini constructs tailored 7-day training modules reviewing weak spots.
				</p>
			</div>
			<Button class="bg-blue-600 hover:bg-blue-700 text-white text-xs h-10 px-4 font-semibold" onclick={generateRoadmap} disabled={isGenerating}>
				{#if isGenerating}Generating roadmap...{:else}Generate 7-Day Plan{/if}
			</Button>
		</div>
	</Card>

	<Card class="border-slate-200 bg-white p-6">
		{#if loading}
			<div class="flex flex-col items-center justify-center p-12 gap-3">
				<div class="animate-spin rounded-full h-8 w-8 border-4 border-slate-200 border-t-blue-600"></div>
				<p class="text-sm text-slate-500 font-medium">Loading plans...</p>
			</div>
		{:else if roadmaps.length === 0}
			<div class="flex flex-col items-center justify-center p-16 text-center gap-1.5">
				<h3 class="text-base font-bold text-slate-900">No study roadmaps found</h3>
				<p class="text-xs text-slate-500 max-w-[320px]">Click "Generate 7-Day Plan" above to create your first learning path.</p>
			</div>
		{:else}
			{@const activeRoadmap = roadmaps[0]}
			<div class="flex flex-col">
				<h3 class="text-base font-bold text-slate-800">{activeRoadmap.title}</h3>
				<span class="text-[11px] text-slate-400 font-medium mb-8">Generated on: {activeRoadmap.created_on.split('T')[0]}</span>
				
				<div class="flex flex-col gap-6 relative pl-6 border-l border-slate-200">
					{#each activeRoadmap.roadmap_data.days as day}
						<div class="flex gap-4 relative">
							<!-- Timeline Circle -->
							<div class="w-2.5 h-2.5 bg-blue-600 rounded-full border-2 border-white absolute -left-[30px] top-4 z-10 shadow-sm"></div>

							<div class="w-20 h-8 bg-blue-50 text-blue-700 rounded-full flex items-center justify-center font-bold text-[11px] font-title shrink-0 border border-blue-100/50 mt-1">
								Day {day.day}
							</div>
							<div class="bg-slate-50 border border-slate-200/60 p-5 rounded-xl flex-1 hover:border-slate-300 transition-all">
								<h4 class="text-sm font-bold text-slate-800 mb-2">{day.focus}</h4>
								<ul class="list-disc pl-5 text-xs text-slate-600 leading-relaxed flex flex-col gap-1">
									{#each day.tasks as task}
										<li>{task}</li>
									{/each}
								</ul>
							</div>
						</div>
					{/each}
				</div>
			</div>
		{/if}
	</Card>
</div>
