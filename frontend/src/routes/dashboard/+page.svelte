<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { api, ApiError } from '$lib/api';
	import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '$lib/components/ui/card';
	import { Progress } from '$lib/components/ui/progress';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';

	interface DashboardSummary {
		solved_count: number;
		attempted_count: number;
		streak: number;
		revision_due_count: number;
		weak_topics: Array<{ topic_name: string; score: number }>;
		recommended_problems: Array<{ id: number; title: string; difficulty: string; topic: string }>;
	}

	let stats = $state<DashboardSummary | null>(null);
	let loading = $state(true);
	let error = $state('');

	onMount(async () => {
		const token = localStorage.getItem('token');
		if (!token) {
			goto('/login');
			return;
		}

		try {
			stats = await api<DashboardSummary>('/dashboard/summary');
		} catch (err: any) {
			if (err instanceof ApiError && err.status === 401) {
				localStorage.removeItem('token');
				localStorage.removeItem('user');
				goto('/login');
				return;
			}
			error = err.message || 'Could not fetch dashboard summary';
		} finally {
			loading = false;
		}
	});
</script>

{#if loading}
	<div class="flex flex-col items-center justify-center min-h-[400px] gap-3">
		<div class="animate-spin rounded-full h-8 w-8 border-4 border-slate-200 border-t-blue-600"></div>
		<p class="text-sm text-slate-500 font-medium">Analyzing your DSA stats...</p>
	</div>
{:else if error}
	<div class="flex items-center justify-center min-h-[400px]">
		<Card class="max-w-[400px] text-center border-slate-200 p-6">
			<CardHeader>
				<CardTitle class="text-rose-600 text-lg">Connection Error</CardTitle>
				<CardDescription>{error}</CardDescription>
			</CardHeader>
			<CardContent class="pt-2">
				<Button class="bg-blue-600 hover:bg-blue-700 text-white" onclick={() => window.location.reload()}>Retry</Button>
			</CardContent>
		</Card>
	</div>
{:else if stats}
	<div class="flex flex-col gap-6">
		<!-- Stat Cards -->
		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
			<Card class="flex items-center gap-4 p-5 hover:shadow-md transition-all border-slate-200 bg-white">
				<div class="w-12 h-12 rounded-xl flex items-center justify-center text-xl bg-emerald-50 text-emerald-600 border border-emerald-100/50">
					✓
				</div>
				<div class="flex flex-col">
					<span class="text-xs text-slate-500 font-medium">Problems Solved</span>
					<span class="text-2xl font-bold text-slate-900 font-title">{stats.solved_count}</span>
				</div>
			</Card>

			<Card class="flex items-center gap-4 p-5 hover:shadow-md transition-all border-slate-200 bg-white">
				<div class="w-12 h-12 rounded-xl flex items-center justify-center text-xl bg-blue-50 text-blue-600 border border-blue-100/50">
					✏️
				</div>
				<div class="flex flex-col">
					<span class="text-xs text-slate-500 font-medium">Total Attempted</span>
					<span class="text-2xl font-bold text-slate-900 font-title">{stats.attempted_count}</span>
				</div>
			</Card>

			<Card class="flex items-center gap-4 p-5 hover:shadow-md transition-all border-slate-200 bg-white">
				<div class="w-12 h-12 rounded-xl flex items-center justify-center text-xl bg-amber-50 text-amber-600 border border-amber-100/50">
					🔥
				</div>
				<div class="flex flex-col">
					<span class="text-xs text-slate-500 font-medium">Current Streak</span>
					<span class="text-2xl font-bold text-slate-900 font-title">{stats.streak} Days</span>
				</div>
			</Card>

			<Card class="flex items-center gap-4 p-5 hover:shadow-md transition-all border-slate-200 bg-white">
				<div class="w-12 h-12 rounded-xl flex items-center justify-center text-xl bg-slate-50 text-slate-600 border border-slate-100">
					⏳
				</div>
				<div class="flex flex-col">
					<span class="text-xs text-slate-500 font-medium">Revision Due</span>
					<span class="text-2xl font-bold font-title {stats.revision_due_count > 0 ? 'text-amber-600' : 'text-slate-900'}">
						{stats.revision_due_count} Problems
					</span>
				</div>
			</Card>
		</div>

		<!-- Main Sections -->
		<div class="grid grid-cols-1 lg:grid-cols-5 gap-6">
			<!-- Left Column: Recommendations (3/5 width) -->
			<div class="lg:col-span-3">
				<Card class="h-full border-slate-200 bg-white">
					<CardHeader class="pb-4">
						<CardTitle class="text-lg font-bold text-slate-900">Recommended Next Problems</CardTitle>
						<CardDescription class="text-xs text-slate-500">
							Tailored to strengthen your understanding of weak topics.
						</CardDescription>
					</CardHeader>
					<CardContent class="flex flex-col gap-3">
						{#each stats.recommended_problems as problem}
							<div class="flex items-center justify-between p-4 border border-slate-100 rounded-xl bg-slate-50/50 hover:border-slate-200 transition-all">
								<div class="flex flex-col gap-1.5">
									<span class="text-sm font-semibold text-slate-800">{problem.title}</span>
									<span class="text-[10px] font-bold text-slate-500 bg-slate-200/60 px-2 py-0.5 rounded-full w-fit">
										{problem.topic}
									</span>
								</div>
								<div class="flex items-center gap-3">
									<Badge variant="outline" class="text-xs font-semibold py-0.5 rounded-full {problem.difficulty === 'Easy' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : problem.difficulty === 'Medium' ? 'bg-amber-50 text-amber-700 border-amber-200' : 'bg-rose-50 text-rose-700 border-rose-200'}">
										{problem.difficulty}
									</Badge>
									<Button variant="secondary" size="sm" class="text-xs py-1 px-3 h-8 bg-blue-50 text-blue-600 hover:bg-blue-100" href="/problems/{problem.id}">
										Solve
									</Button>
								</div>
							</div>
						{/each}
					</CardContent>
				</Card>
			</div>

			<!-- Right Column: Weak Topics (2/5 width) -->
			<div class="lg:col-span-2">
				<Card class="h-full border-slate-200 bg-white">
					<CardHeader class="pb-4">
						<CardTitle class="text-lg font-bold text-slate-900">Weak Topics Tracking</CardTitle>
						<CardDescription class="text-xs text-slate-500">
							Focus areas calculated from your recent submission scores.
						</CardDescription>
					</CardHeader>
					<CardContent class="flex flex-col gap-4">
						{#each stats.weak_topics as topic}
							<div class="flex flex-col gap-2">
								<div class="flex justify-between items-center text-sm">
									<span class="font-semibold text-slate-800">{topic.topic_name}</span>
									<span class="text-[13px] font-medium {topic.score < 50 ? 'text-rose-600' : topic.score < 75 ? 'text-amber-600' : 'text-emerald-600'}">
										{topic.score}% proficiency
									</span>
								</div>
								<!-- Progress Bar -->
								<div class="w-full">
									<!-- Svelte shadcn progress element -->
									<Progress value={topic.score} class="h-2 bg-slate-100 {topic.score < 50 ? '[&>div]:bg-rose-500' : topic.score < 75 ? '[&>div]:bg-amber-500' : '[&>div]:bg-emerald-500'}" />
								</div>
							</div>
						{/each}
					</CardContent>
				</Card>
			</div>
		</div>
	</div>
{/if}
