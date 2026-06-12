<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { api } from '$lib/api';
	import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '$lib/components/ui/card';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';

	interface RevisionItem {
		id: number;
		problem_id: number;
		due_date: string;
		reason?: string;
		status: string;
	}

	let queue = $state<RevisionItem[]>([]);
	let loading = $state(true);

	onMount(async () => {
		if (!localStorage.getItem('token')) {
			goto('/login');
			return;
		}
		await loadQueue();
	});

	async function loadQueue() {
		try {
			queue = await api<RevisionItem[]>('/revision');
		} catch (e) {
			console.error(e);
		} finally {
			loading = false;
		}
	}

	async function markComplete(id: number) {
		try {
			await api(`/revision/${id}/complete`, { method: 'POST' });
			await loadQueue();
		} catch (e) {
			console.error(e);
		}
	}
</script>

<div class="flex flex-col gap-6 max-w-[900px] mx-auto w-full">
	<Card class="border-slate-200 bg-white p-6">
		<CardHeader class="p-0">
			<CardTitle class="text-lg font-bold text-slate-900">DSA Revision Queue</CardTitle>
			<CardDescription class="text-xs text-slate-500">
				Interval-spaced revisions optimize logic retention. Solve overdue items today!
			</CardDescription>
		</CardHeader>
	</Card>

	<Card class="border-slate-200 bg-white p-6">
		{#if loading}
			<div class="flex flex-col items-center justify-center p-12 gap-3">
				<div class="animate-spin rounded-full h-8 w-8 border-4 border-slate-200 border-t-blue-600"></div>
				<p class="text-sm text-slate-500 font-medium">Loading queue...</p>
			</div>
		{:else if queue.length === 0}
			<div class="flex flex-col items-center justify-center p-16 text-center gap-1.5">
				<h3 class="text-base font-bold text-slate-900">All caught up!</h3>
				<p class="text-xs text-slate-500 max-w-[320px]">Your revision queue is empty. Keep solving problems to schedule revisions.</p>
			</div>
		{:else}
			<div class="flex flex-col gap-3">
				{#each queue as item}
					<div class="flex items-center justify-between p-4 border border-slate-100 rounded-xl bg-slate-50/50 hover:border-slate-200 transition-all {item.status === 'completed' ? 'opacity-60 bg-slate-50' : ''}">
						<div class="flex flex-col gap-1">
							<span class="text-sm font-semibold text-slate-800">Due: {item.due_date}</span>
							<span class="text-[11px] text-slate-400 font-medium">Reason: {item.reason || 'Recent Attempt'}</span>
						</div>

						<div class="flex items-center gap-3">
							{#if item.status === 'pending'}
								<Button variant="outline" size="sm" class="text-xs py-1 px-3 h-8 border-slate-200 bg-white hover:bg-slate-50" onclick={() => markComplete(item.id)}>
									Mark Revised
								</Button>
								<Button class="bg-blue-600 hover:bg-blue-700 text-white text-xs py-1 px-3 h-8" href="/problems/{item.problem_id}">
									Solve Again
								</Button>
							{:else}
								<Badge class="bg-emerald-50 text-emerald-700 border border-emerald-200/50 hover:bg-emerald-50 font-bold px-2.5 py-0.5 rounded-full text-xs">
									Revised ✓
								</Badge>
							{/if}
						</div>
					</div>
				{/each}
			</div>
		{/if}
	</Card>
</div>
