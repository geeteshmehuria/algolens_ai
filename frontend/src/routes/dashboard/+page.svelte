<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { api, ApiError } from '$lib/api';
	import { getToken, getStoredUser, clearAuth } from '$lib/auth';
	import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '$lib/components/ui/card';
	import { Progress } from '$lib/components/ui/progress';
	import { Button } from '$lib/components/ui/button';
	import StatCard from '$lib/components/app/StatCard.svelte';
	import DifficultyBadge from '$lib/components/app/DifficultyBadge.svelte';
	import EmptyState from '$lib/components/app/EmptyState.svelte';
	import LoadingState from '$lib/components/app/LoadingState.svelte';
	import StreakHeatmap from '$lib/components/app/StreakHeatmap.svelte';
	import ProgressOverviewCard from '$lib/components/dashboard/progress-overview-card.svelte';
	import TimeSpentCard from '$lib/components/dashboard/time-spent-card.svelte';

	interface DashboardSummary {
		solved_count: number;
		attempted_count: number;
		streak: number;
		revision_due_count: number;
		weak_topics: Array<{ topic_id: number; topic_name: string; score: number }>;
		recommended_problems: Array<{ id: number; title: string; difficulty: string; topic: string }>;
	}

	interface TopicNoteItem {
		state?: { status: string } | null;
	}

	let stats = $state<DashboardSummary | null>(null);
	let activity = $state<Array<{ date: string; count: number }>>([]);
	let topicNotes = $state<TopicNoteItem[]>([]);
	let loading = $state(true);
	let error = $state('');

	// Progress Overview — real counts derived from the user's topic-note state.
	let progress = $derived.by(() => {
		const total = topicNotes.length;
		let completed = 0;
		let inProgress = 0;
		for (const t of topicNotes) {
			const s = t.state?.status;
			if (s === 'completed' || s === 'revised') completed++;
			else if (t.state) inProgress++; // has state but still 'reading'
		}
		return { total, completed, inProgress, notStarted: total - completed - inProgress };
	});

	// Weekly activity — real attempts/day from the activity feed (last 7 days),
	// with a week-over-week change vs the prior 7 days.
	const DAY_LABELS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
	let weekly = $derived.by(() => {
		const sum = (rows: Array<{ count: number }>) => rows.reduce((s, r) => s + r.count, 0);
		const last7 = activity.slice(-7);
		const prev7 = activity.slice(-14, -7);
		const total = sum(last7);
		const prevTotal = sum(prev7);
		const change =
			prevTotal > 0 ? Math.round(((total - prevTotal) / prevTotal) * 100) : total > 0 ? 100 : null;
		const bars = last7.map((r) => ({
			label: DAY_LABELS[new Date(r.date + 'T00:00:00').getDay()] ?? '',
			value: r.count
		}));
		return { total, change, bars };
	});

	let firstName = $derived.by(() => {
		const u = getStoredUser<{ full_name?: string }>();
		return (u?.full_name || '').split(' ')[0] || '';
	});

	onMount(async () => {
		if (!getToken()) {
			goto('/login');
			return;
		}

		try {
			stats = await api<DashboardSummary>('/dashboard/summary');
			// Activity feeds the heatmap; it's non-critical, so a failure here must
			// not blank the dashboard.
			api<Array<{ date: string; count: number }>>('/dashboard/activity')
				.then((rows) => (activity = rows))
				.catch(() => (activity = []));
			// Topic-note state powers the Progress Overview card; non-critical.
			api<TopicNoteItem[]>('/me/topic-notes')
				.then((rows) => (topicNotes = rows))
				.catch(() => (topicNotes = []));
		} catch (err: any) {
			if (err instanceof ApiError && err.status === 401) {
				clearAuth();
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

		<!-- Continue card: nudge the user toward the single best next action -->
		{#if stats.revision_due_count > 0}
			<a
				href="/revision"
				class="lift flex items-center justify-between gap-4 rounded-2xl border border-amber-200 bg-amber-50/60 p-5 hover:shadow-md"
			>
				<div class="flex items-center gap-4">
					<div class="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-amber-100 text-xl">⏳</div>
					<div class="flex flex-col">
						<span class="text-xs font-semibold uppercase tracking-wide text-amber-700">Due for revision</span>
						<span class="font-title text-base font-bold text-slate-900">Start revision ({stats.revision_due_count} due)</span>
					</div>
				</div>
				<span class="hidden shrink-0 rounded-lg bg-amber-600 px-4 py-2 text-sm font-semibold text-white sm:inline">Start →</span>
			</a>
		{:else if stats.recommended_problems.length > 0}
			{@const next = stats.recommended_problems[0]}
			<a
				href="/problems/{next.id}"
				class="lift flex items-center justify-between gap-4 rounded-2xl border border-blue-200 bg-blue-50/50 p-5 hover:shadow-md"
			>
				<div class="flex items-center gap-4">
					<div class="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-blue-100 text-xl">▶️</div>
					<div class="flex min-w-0 flex-col">
						<span class="text-xs font-semibold uppercase tracking-wide text-blue-700">Pick up where you left off</span>
						<span class="truncate font-title text-base font-bold text-slate-900">{next.title}</span>
					</div>
				</div>
				<span class="hidden shrink-0 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white sm:inline">Solve →</span>
			</a>
		{/if}

		<!-- Stat Cards -->
		<div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
			<StatCard label="Problems Solved" value={stats.solved_count} accent="emerald">
				{#snippet icon()}
					<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.8" stroke="currentColor" class="h-6 w-6">
						<path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
					</svg>
				{/snippet}
			</StatCard>
			<StatCard label="Total Attempted" value={stats.attempted_count} accent="teal">
				{#snippet icon()}
					<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.8" stroke="currentColor" class="h-6 w-6">
						<path stroke-linecap="round" stroke-linejoin="round" d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0 1 15.75 21H5.25A2.25 2.25 0 0 1 3 18.75V8.25A2.25 2.25 0 0 1 5.25 6H10" />
					</svg>
				{/snippet}
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
				{#snippet icon()}
					<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.8" stroke="currentColor" class="h-6 w-6">
						<path stroke-linecap="round" stroke-linejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
					</svg>
				{/snippet}
			</StatCard>
		</div>

		<!-- Progress Overview + Weekly Activity -->
		<div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
			<ProgressOverviewCard
				completed={progress.completed}
				inProgress={progress.inProgress}
				notStarted={progress.notStarted}
				total={progress.total}
				href="/topics"
			/>
			<TimeSpentCard
				title="Weekly Activity"
				subtitle="Problems attempted in the last 7 days"
				headline={`${weekly.total} attempts`}
				changePercent={weekly.change}
				bars={weekly.bars}
			/>
		</div>

		<!-- Activity heatmap -->
		<Card class="border-slate-200 bg-white">
			<CardHeader class="pb-2">
				<div class="flex items-center justify-between gap-3">
					<div>
						<CardTitle class="font-title text-lg font-bold text-slate-900">Activity</CardTitle>
						<CardDescription class="text-xs text-slate-500">Your attempts over the last 12 weeks.</CardDescription>
					</div>
					<div class="flex items-center gap-1.5 rounded-full border border-amber-200/60 bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-800">
						<span>🔥</span>
						<span>{stats.streak}-day streak</span>
					</div>
				</div>
			</CardHeader>
			<CardContent class="overflow-x-auto">
				{#if activity.length}
					<StreakHeatmap data={activity} />
				{:else}
					<p class="py-4 text-sm text-slate-400">No activity recorded yet — solve a problem to start your heatmap.</p>
				{/if}
			</CardContent>
		</Card>

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
							<a
								href="/problems?topic={topic.topic_id}"
								class="group flex flex-col gap-2 rounded-lg p-2 -m-2 transition-colors hover:bg-slate-50"
							>
								<div class="flex items-center justify-between text-sm">
									<span class="font-semibold text-slate-800 group-hover:text-blue-600">{topic.topic_name}</span>
									<span class="text-[13px] font-medium {topic.score < 50 ? 'text-rose-600' : topic.score < 75 ? 'text-amber-600' : 'text-emerald-600'}">
										{topic.score}% proficiency
									</span>
								</div>
								<Progress value={topic.score} class="h-2 bg-slate-100 {topic.score < 50 ? '[&>div]:bg-rose-500' : topic.score < 75 ? '[&>div]:bg-amber-500' : '[&>div]:bg-emerald-500'}" />
							</a>
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
