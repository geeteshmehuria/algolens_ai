<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { api } from '$lib/api';
	import { getToken } from '$lib/auth';
	import { loadContents } from '$lib/stores/common';
	import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '$lib/components/ui/card';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';

	interface ImportRun {
		id: number;
		source: string;
		trigger: string;
		status: string;
		started_at: string;
		completed_at?: string | null;
		imported_count: number;
		skipped_duplicate_count: number;
		failed_count: number;
		error_log?: string | null;
	}

	interface CoverageRow { category: string; current: number; target: number; gap: number; }

	interface ImportStatus {
		latest_run: ImportRun | null;
		coverage: CoverageRow[];
		review_queue_count: number;
		ai_enabled: boolean;
		leetcode_enabled: boolean;
		daily_limit: number;
	}

	interface ImportedProblem {
		id: number;
		title: string;
		difficulty: string;
		source_name?: string;
		attribution?: string;
		leetcode_url?: string;
		interview_frequency_score?: number | null;
	}

	let status = $state<ImportStatus | null>(null);
	let runs = $state<ImportRun[]>([]);
	let queue = $state<ImportedProblem[]>([]);
	let loading = $state(true);
	let running = $state(false);
	let message = $state('');
	let error = $state('');
	let csvText = $state('');
	let uploading = $state(false);

	async function refresh() {
		[status, runs, queue] = await Promise.all([
			api<ImportStatus>('/admin/problem-import/status'),
			api<ImportRun[]>('/admin/problem-import/runs?limit=10'),
			api<ImportedProblem[]>('/admin/problem-import/problems?import_status=review_required')
		]);
	}

	onMount(async () => {
		if (!getToken()) {
			goto('/login');
			return;
		}
		try {
			const contents = await loadContents();
			if (!contents.user?.roles?.includes('admin')) {
				goto('/dashboard');
				return;
			}
			await refresh();
		} catch (e: any) {
			error = e?.message ?? 'Failed to load import dashboard.';
		} finally {
			loading = false;
		}
	});

	async function runImport() {
		running = true;
		message = '';
		error = '';
		try {
			const run = await api<ImportRun>('/admin/problem-import/run', {
				method: 'POST',
				body: JSON.stringify({})
			});
			message = `Run #${run.id} ${run.status}: imported ${run.imported_count}, skipped ${run.skipped_duplicate_count}, failed ${run.failed_count}.`;
			await refresh();
		} catch (e: any) {
			error = e?.message ?? 'Import run failed.';
		} finally {
			running = false;
		}
	}

	async function setStatus(id: number, action: 'publish' | 'archive') {
		error = '';
		try {
			await api(`/admin/problem-import/problems/${id}/${action}`, { method: 'POST' });
			queue = queue.filter((p) => p.id !== id);
			if (status) status.review_queue_count = Math.max(0, status.review_queue_count - 1);
		} catch (e: any) {
			error = e?.message ?? `Could not ${action} problem.`;
		}
	}

	async function uploadCsv() {
		uploading = true;
		message = '';
		error = '';
		try {
			const run = await api<ImportRun>('/admin/problem-import/upload', {
				method: 'POST',
				body: JSON.stringify({ csv_text: csvText })
			});
			message = `Upload run #${run.id} ${run.status}: imported ${run.imported_count}, skipped ${run.skipped_duplicate_count}, failed ${run.failed_count}.`;
			csvText = '';
			await refresh();
		} catch (e: any) {
			error = e?.message ?? 'Upload failed.';
		} finally {
			uploading = false;
		}
	}

	function statusColor(s: string) {
		if (s === 'success') return 'bg-emerald-50 text-emerald-700 border-emerald-200';
		if (s === 'partial') return 'bg-amber-50 text-amber-700 border-amber-200';
		if (s === 'failed') return 'bg-rose-50 text-rose-700 border-rose-200';
		return 'bg-muted text-muted-foreground border-border';
	}
</script>

<div class="flex flex-col gap-6 max-w-[1000px] mx-auto w-full">
	<Card class="border-border bg-card p-6">
		<CardHeader class="p-0">
			<CardTitle class="text-lg font-bold text-foreground">Problem Import</CardTitle>
			<CardDescription class="text-xs text-muted-foreground">
				Import practice problems from curated public lists + original AI-generated practice.
				Imported problems land as <b>review_required</b> and are hidden from users until you publish them.
				Only public metadata and AlgoLens-original content are stored — never third-party statements or premium data.
			</CardDescription>
		</CardHeader>
	</Card>

	{#if error}
		<div class="bg-rose-50 border border-rose-100 text-rose-600 text-xs rounded-lg p-3.5 font-medium">{error}</div>
	{/if}
	{#if message}
		<div class="bg-emerald-50 border border-emerald-100 text-emerald-600 text-xs rounded-lg p-3.5 font-medium">{message}</div>
	{/if}

	{#if loading}
		<div class="flex items-center justify-center p-12 gap-3">
			<div class="animate-spin rounded-full h-8 w-8 border-4 border-border border-t-primary"></div>
			<p class="text-sm text-muted-foreground font-medium">Loading…</p>
		</div>
	{:else if status}
		<!-- Run + summary -->
		<Card class="border-border bg-card p-6">
			<div class="flex flex-wrap items-center justify-between gap-4">
				<div class="flex flex-col gap-1">
					<p class="text-sm font-bold text-foreground">Run import now</p>
					<p class="text-xs text-muted-foreground">
						Up to {status.daily_limit} problems · AI source {status.ai_enabled ? 'on' : 'off'} ·
						LeetCode metadata {status.leetcode_enabled ? 'on' : 'off'} · {status.review_queue_count} awaiting review
					</p>
				</div>
				<Button class="h-10 px-6 text-xs font-semibold" disabled={running} onclick={runImport}>
					{#if running}Running…{:else}Run import{/if}
				</Button>
			</div>
		</Card>

		<!-- Coverage -->
		<Card class="border-border bg-card p-6">
			<CardTitle class="text-sm font-bold text-foreground mb-3">Topic coverage</CardTitle>
			<div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2">
				{#each status.coverage as row}
					<div class="rounded-lg border border-border p-2.5 text-xs">
						<div class="font-semibold text-foreground truncate">{row.category}</div>
						<div class="text-muted-foreground">
							{row.current}/{row.target}
							{#if row.gap > 0}<span class="text-amber-600 font-semibold"> · gap {row.gap}</span>{/if}
						</div>
					</div>
				{/each}
			</div>
		</Card>

		<!-- Review queue -->
		<Card class="border-border bg-card p-6">
			<CardTitle class="text-sm font-bold text-foreground mb-3">Review queue ({queue.length})</CardTitle>
			{#if queue.length === 0}
				<p class="text-xs text-muted-foreground">No problems awaiting review.</p>
			{:else}
				<div class="flex flex-col divide-y divide-border">
					{#each queue as p}
						<div class="flex flex-wrap items-center justify-between gap-3 py-3">
							<div class="flex flex-col gap-0.5 min-w-0">
								<div class="flex items-center gap-2">
									<span class="font-semibold text-sm text-foreground truncate">{p.title}</span>
									<Badge class="text-[10px] py-0 {p.difficulty === 'Easy' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : p.difficulty === 'Medium' ? 'bg-amber-50 text-amber-700 border-amber-200' : 'bg-rose-50 text-rose-700 border-rose-200'}">{p.difficulty}</Badge>
								</div>
								<span class="text-[11px] text-muted-foreground truncate">{p.attribution ?? p.source_name ?? ''}</span>
							</div>
							<div class="flex items-center gap-2">
								{#if p.leetcode_url}
									<a href={p.leetcode_url} target="_blank" rel="noopener noreferrer" class="text-xs text-primary hover:underline">Source ↗</a>
								{/if}
								<Button class="h-8 px-3 text-xs" onclick={() => setStatus(p.id, 'publish')}>Publish</Button>
								<Button variant="outline" class="h-8 px-3 text-xs" onclick={() => setStatus(p.id, 'archive')}>Archive</Button>
							</div>
						</div>
					{/each}
				</div>
			{/if}
		</Card>

		<!-- Manual upload -->
		<Card class="border-border bg-card p-6">
			<CardTitle class="text-sm font-bold text-foreground mb-1">Manual CSV import</CardTitle>
			<CardDescription class="text-xs text-muted-foreground mb-3">
				Header row: <code>title,difficulty,topic,slug,url</code>. Deduplicated automatically.
			</CardDescription>
			<textarea
				bind:value={csvText}
				rows="5"
				placeholder={'title,difficulty,topic,slug,url\nTwo Sum,Easy,arrays,two-sum,https://leetcode.com/problems/two-sum/'}
				class="w-full rounded-lg border border-input bg-card p-3 text-xs font-mono text-foreground focus:outline-none focus:ring-2 focus:ring-ring/25"
			></textarea>
			<Button class="mt-3 h-9 px-5 text-xs font-semibold" disabled={uploading || !csvText.trim()} onclick={uploadCsv}>
				{#if uploading}Uploading…{:else}Import CSV{/if}
			</Button>
		</Card>

		<!-- Run history -->
		<Card class="border-border bg-card p-6">
			<CardTitle class="text-sm font-bold text-foreground mb-3">Recent runs</CardTitle>
			{#if runs.length === 0}
				<p class="text-xs text-muted-foreground">No runs yet.</p>
			{:else}
				<div class="flex flex-col divide-y divide-border text-xs">
					{#each runs as r}
						<div class="flex flex-wrap items-center justify-between gap-3 py-2.5">
							<div class="flex items-center gap-2">
								<span class="font-mono text-muted-foreground">#{r.id}</span>
								<Badge class="text-[10px] py-0 border {statusColor(r.status)}">{r.status}</Badge>
								<span class="text-muted-foreground">{r.trigger}</span>
							</div>
							<div class="text-muted-foreground">
								imported {r.imported_count} · skipped {r.skipped_duplicate_count} · failed {r.failed_count}
							</div>
						</div>
					{/each}
				</div>
			{/if}
		</Card>
	{/if}
</div>
