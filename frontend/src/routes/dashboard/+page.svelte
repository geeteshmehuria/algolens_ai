<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { api, ApiError } from '$lib/api';
	import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '$lib/components/ui/card';
	import { Progress } from '$lib/components/ui/progress';
	import { Button } from '$lib/components/ui/button';
	import StatCard from '$lib/components/app/StatCard.svelte';
	import DifficultyBadge from '$lib/components/app/DifficultyBadge.svelte';
	import EmptyState from '$lib/components/app/EmptyState.svelte';
	import LoadingState from '$lib/components/app/LoadingState.svelte';

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

	let firstName = $derived.by(() => {
		try {
			const u = JSON.parse(localStorage.getItem('user') || '{}');
			return (u.full_name || '').split(' ')[0] || '';
		} catch {
			return '';
		}
	});

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
	<LoadingState message="Analyzing your DSA stats…" class="min-h-[400px]" />
{:else if error}
	<div class="flex items-center justify-center min-h-[400px]">
		<Card class="max-w-[420px] text-center border-slate-200 p-6">
			<CardHeader>
				<CardTitle class="text-rose-600 text-lg">Couldn't load your dashboard</CardTitle>
				<CardDescription>{error}</CardDescription>
			</CardHeader>
			<CardContent class="pt-2">
				<Button class="bg-blue-600 hover:bg-blue-700 text-white" onclick={() => window.location.reload()}>Try again</Button>
			</CardContent>
		</Card>
	</div>
{:else if stats}
	<div class="flex flex-col gap-6">
		<!-- Hero / welcome -->
		<div class="surface-hero flex flex-col gap-1 rounded-2xl border border-blue-100/70 p-6">
			<h2 class="font-title text-2xl font-bold tracking-tight text-slate-900">
				Welcome back{firstName ? `, ${firstName}` : ''} 👋
			</h2>
			<p class="text-sm text-slate-600">
				Here's a snapshot of your progress. Keep your streak alive and tackle a recommended problem.
			</p>
		</div>

		<!-- Stat Cards -->
		<div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
			<StatCard label="Problems Solved" value={stats.solved_count} accent="emerald">
				{#snippet icon()}✓{/snippet}
			</StatCard>
			<StatCard label="Total Attempted" value={stats.attempted_count} accent="blue">
				{#snippet icon()}✏️{/snippet}
			</StatCard>
			<StatCard label="Current Streak" value={`${stats.streak} Days`} accent="amber">
				{#snippet icon()}🔥{/snippet}
			</StatCard>
			<StatCard
				label="Revision Due"
				value={`${stats.revision_due_count} Problems`}
				accent="slate"
				valueClass={stats.revision_due_count > 0 ? 'text-amber-600' : ''}
			>
				{#snippet icon()}⏳{/snippet}
			</StatCard>
		</div>

		<!-- Main Sections -->
		<div class="grid grid-cols-1 gap-6 lg:grid-cols-5">
			<!-- Left Column: Recommendations (3/5 width) -->
			<div class="lg:col-span-3">
				<Card class="h-full border-slate-200 bg-white">
					<CardHeader class="pb-4">
						<CardTitle class="font-title text-lg font-bold text-slate-900">Recommended Next Problems</CardTitle>
						<CardDescription class="text-xs text-slate-500">
							Tailored to strengthen your understanding of weak topics.
						</CardDescription>
					</CardHeader>
					<CardContent class="flex flex-col gap-3">
						{#each stats.recommended_problems as problem (problem.id)}
							<a
								href="/problems/{problem.id}"
								class="lift flex items-center justify-between gap-3 rounded-xl border border-slate-100 bg-slate-50/50 p-4 hover:border-blue-200 hover:bg-blue-50/40 hover:shadow-sm"
							>
								<div class="flex min-w-0 flex-col gap-1.5">
									<span class="truncate text-sm font-semibold text-slate-800">{problem.title}</span>
									<span class="w-fit rounded-full bg-slate-200/60 px-2 py-0.5 text-[10px] font-bold text-slate-500">
										{problem.topic}
									</span>
								</div>
								<div class="flex shrink-0 items-center gap-3">
									<DifficultyBadge difficulty={problem.difficulty} />
									<span class="hidden text-xs font-semibold text-blue-600 sm:inline">Solve →</span>
								</div>
							</a>
						{:else}
							<EmptyState
								title="No recommendations yet"
								description="Solve a few problems and AlgoLens will suggest what to practice next."
								class="border-0 bg-transparent py-10"
							>
								{#snippet action()}
									<Button class="bg-blue-600 hover:bg-blue-700 text-white" href="/problems">Browse problems</Button>
								{/snippet}
							</EmptyState>
						{/each}
					</CardContent>
				</Card>
			</div>

			<!-- Right Column: Weak Topics (2/5 width) -->
			<div class="lg:col-span-2">
				<Card class="h-full border-slate-200 bg-white">
					<CardHeader class="pb-4">
						<CardTitle class="font-title text-lg font-bold text-slate-900">Weak Topics Tracking</CardTitle>
						<CardDescription class="text-xs text-slate-500">
							Focus areas calculated from your recent submission scores.
						</CardDescription>
					</CardHeader>
					<CardContent class="flex flex-col gap-4">
						{#each stats.weak_topics as topic}
							<div class="flex flex-col gap-2">
								<div class="flex items-center justify-between text-sm">
									<span class="font-semibold text-slate-800">{topic.topic_name}</span>
									<span class="text-[13px] font-medium {topic.score < 50 ? 'text-rose-600' : topic.score < 75 ? 'text-amber-600' : 'text-emerald-600'}">
										{topic.score}% proficiency
									</span>
								</div>
								<Progress value={topic.score} class="h-2 bg-slate-100 {topic.score < 50 ? '[&>div]:bg-rose-500' : topic.score < 75 ? '[&>div]:bg-amber-500' : '[&>div]:bg-emerald-500'}" />
							</div>
						{:else}
							<EmptyState
								title="No data yet"
								description="Your weak topics will appear here once you submit a few solutions."
								class="border-0 bg-transparent py-10"
							/>
						{/each}
					</CardContent>
				</Card>
			</div>
		</div>
	</div>
{/if}
