<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '$lib/components/ui/card';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import * as Tabs from '$lib/components/ui/tabs';
	import { api } from '$lib/api';
	import LoadingState from '$lib/components/app/LoadingState.svelte';
	import DifficultyBadge from '$lib/components/app/DifficultyBadge.svelte';
	import { Skeleton } from '$lib/components/ui/skeleton';

	interface Problem {
		id: number;
		title: string;
		difficulty: string;
		topic_id: number;
		pattern_id: number;
		description: string;
		constraints_text?: string;
		examples?: any[];
		starter_code?: string;
		leetcode_url?: string;
	}

	interface AIExplanation {
		simple_explanation: string;
		brute_force: string;
		optimized_approach: string;
		pseudocode: string[];
		time_complexity: string;
		space_complexity: string;
		common_mistakes: string[];
		pattern: string;
	}

	interface AnimationData {
		animation_type: string;
		input: any;
		steps: any[];
	}

	interface CodeReview {
		is_correct: boolean;
		logic_feedback: string;
		bugs: string[];
		missed_edge_cases: string[];
		time_complexity: string;
		space_complexity: string;
		better_approach: string;
		dsa_pattern: string;
		score: number;
	}

	const problemId = parseInt(page.params.id || '0');

	// Core State
	let problem = $state<Problem | null>(null);
	let loading = $state(true);
	let activeTab = $state('logic');

	// Code editor state
	let submittedCode = $state('');
	let isSubmittingCode = $state(false);
	let codeReview = $state<CodeReview | null>(null);
	let hintText = $state('');
	let activeHintLevel = $state(0);

	// AI Explanation state
	let aiExplanation = $state<AIExplanation | null>(null);
	let isGeneratingExplanation = $state(false);
	// Per-feature errors so a failure in one generator can't mask another's
	// content. `aiError` is kept for the AI code-review / hint flows.
	let explanationError = $state('');
	let animationError = $state('');
	let aiError = $state('');

	// User problem state (bookmark / note / confidence)
	let isBookmarked = $state(false);
	let confidence = $state<number | null>(null);
	let noteContent = $state('');
	let noteStatus = $state<'' | 'saving' | 'saved' | 'error'>('');

	// Animation player state
	let animationData = $state<AnimationData | null>(null);
	let isGeneratingAnimation = $state(false);
	let currentStepIndex = $state(0);
	let isPlaying = $state(false);
	let playInterval = $state<any>(null);
	let playbackSpeed = $state(1500); // ms

	// The animation is the single source of truth for the "current step"; the
	// Pseudocode/Logic tabs read this derived value (they share currentStepIndex).
	const activeStep = $derived(animationData ? animationData.steps[currentStepIndex] : null);
	// Optional, backend-driven emphasis. We only highlight a complexity pill when
	// a step *explicitly* carries `complexity_focus` ('time' | 'space') — we never
	// infer a mapping ourselves, so when the data is absent the view is unchanged.
	const focusedComplexity = $derived(activeStep?.complexity_focus ?? null);

	// Fetch Data
	onMount(async () => {
		if (!localStorage.getItem('token')) {
			goto('/login');
			return;
		}

		try {
			const data = await api(`/problems/${problemId}`);
			problem = data;
			submittedCode = data.starter_code || 'def solve(nums, target):\n    # Write your Python code here\n    pass';

			const userState = await api(`/problems/${problemId}/user-state`);
			isBookmarked = userState.bookmarked;
			confidence = userState.confidence;
			noteContent = userState.note ?? '';
		} catch (e) {
			console.error(e);
		} finally {
			loading = false;
		}

		// Auto-generate the learning content once the problem is available — the
		// user no longer has to click "Generate". Both endpoints are cached
		// server-side, so repeat visits are cheap. Fire-and-forget (each manages
		// its own loading/error state); honest errors still surface per tab.
		if (problem) {
			handleGenerateExplanation();
			handleGenerateAnimation();
		}
	});

	// Bookmark / confidence / note actions
	async function toggleBookmark() {
		try {
			const res = await api(`/problems/${problemId}/bookmark`, { method: 'POST' });
			isBookmarked = res.bookmarked;
		} catch (e) {
			console.error(e);
		}
	}

	async function setConfidence(level: number) {
		try {
			const res = await api(`/problems/${problemId}/confidence`, {
				method: 'PUT',
				body: JSON.stringify({ confidence: level })
			});
			confidence = res.confidence;
		} catch (e) {
			console.error(e);
		}
	}

	async function saveNote() {
		noteStatus = 'saving';
		try {
			await api(`/problems/${problemId}/note`, {
				method: 'PUT',
				body: JSON.stringify({ content: noteContent })
			});
			noteStatus = 'saved';
			setTimeout(() => (noteStatus = ''), 2500);
		} catch (e) {
			noteStatus = 'error';
		}
	}

	// AI Explanations Generator (also powers the Pseudocode tab)
	async function handleGenerateExplanation() {
		isGeneratingExplanation = true;
		explanationError = '';
		try {
			aiExplanation = await api(`/ai/generate-explanation/${problemId}`, { method: 'POST' });
		} catch (e: any) {
			explanationError = e.message || 'Failed to generate explanation.';
		} finally {
			isGeneratingExplanation = false;
		}
	}

	// AI Animation Steps Generator
	async function handleGenerateAnimation() {
		isGeneratingAnimation = true;
		animationError = '';
		try {
			animationData = await api(`/ai/generate-animation/${problemId}`, { method: 'POST' });
			currentStepIndex = 0;
		} catch (e: any) {
			animationError = e.message || 'Failed to generate animation.';
		} finally {
			isGeneratingAnimation = false;
		}
	}

	// AI Hints Generator
	async function handleGetHint(level: number) {
		activeHintLevel = level;
		hintText = 'Consulting Gemini...';
		try {
			const data = await api('/ai/hint', {
				method: 'POST',
				body: JSON.stringify({ problem_id: problemId, hint_level: level })
			});
			hintText = data.hint_text;
		} catch (e: any) {
			hintText = e.message || 'Failed to fetch hint.';
		}
	}

	// AI Submission Code Review
	async function handleReviewCode() {
		isSubmittingCode = true;
		activeTab = 'review';
		codeReview = null;
		aiError = '';
		try {
			// Log the attempt first; the backend updates its status after review.
			await api(`/problems/${problemId}/attempts`, {
				method: 'POST',
				body: JSON.stringify({
					submitted_code: submittedCode,
					status: 'Reviewing',
					used_hint: activeHintLevel > 0
				})
			});

			codeReview = await api('/ai/review-code', {
				method: 'POST',
				body: JSON.stringify({
					problem_id: problemId,
					submitted_code: submittedCode,
					used_hint: activeHintLevel > 0
				})
			});
		} catch (e: any) {
			aiError = e.message || 'Failed to review code.';
		} finally {
			isSubmittingCode = false;
		}
	}

	// Animation Controls
	function startPlayback() {
		clearInterval(playInterval);
		playInterval = setInterval(() => {
			if (animationData && currentStepIndex < animationData.steps.length - 1) {
				currentStepIndex++;
			} else {
				clearInterval(playInterval);
				isPlaying = false;
			}
		}, playbackSpeed);
	}

	function togglePlay() {
		if (!animationData) return;
		// Restart from the beginning if we're paused at the final step
		if (!isPlaying && currentStepIndex >= animationData.steps.length - 1) {
			currentStepIndex = 0;
		}
		isPlaying = !isPlaying;
		if (isPlaying) startPlayback();
		else clearInterval(playInterval);
	}

	// Speed control: 0.5× = 3000ms, 1× = 1500ms, 2× = 750ms. Restart the
	// interval mid-playback so the new cadence applies immediately.
	function setSpeed(ms: number) {
		playbackSpeed = ms;
		if (isPlaying) startPlayback();
	}

	// Keyboard shortcuts while the Animation tab is active. Ignored when a
	// text field is focused (e.g. code editor / notes) or the range slider has
	// focus (native arrow handling there moves the scrubber instead).
	function handleAnimationKeys(e: KeyboardEvent) {
		if (activeTab !== 'animation' || !animationData) return;
		const el = e.target as HTMLElement | null;
		const tag = el?.tagName;
		if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || el?.isContentEditable) return;
		if (e.key === 'ArrowRight') {
			e.preventDefault();
			stepNext();
		} else if (e.key === 'ArrowLeft') {
			e.preventDefault();
			stepPrev();
		} else if (e.key === ' ' || e.key === 'Spacebar') {
			e.preventDefault();
			togglePlay();
		}
	}

	function resetAnimation() {
		clearInterval(playInterval);
		isPlaying = false;
		currentStepIndex = 0;
	}

	onDestroy(() => clearInterval(playInterval));

	function stepNext() {
		if (animationData && currentStepIndex < animationData.steps.length - 1) {
			currentStepIndex++;
		}
	}

	function stepPrev() {
		if (currentStepIndex > 0) {
			currentStepIndex--;
		}
	}
</script>

<svelte:window onkeydown={handleAnimationKeys} />

{#if loading}
	<LoadingState message="Opening problem statement…" class="min-h-[400px]" />
{:else if !problem}
	<div class="flex items-center justify-center min-h-[400px]">
		<Card class="max-w-[420px] border-slate-200 p-6 text-center">
			<CardHeader>
				<CardTitle class="font-title text-lg text-slate-900">Problem not found</CardTitle>
				<CardDescription>We couldn't load this problem. It may have been removed or the link is incorrect.</CardDescription>
			</CardHeader>
			<CardContent class="flex justify-center gap-2 pt-2">
				<Button variant="outline" onclick={() => window.location.reload()}>Try again</Button>
				<Button class="bg-blue-600 text-white hover:bg-blue-700" href="/problems">Back to problems</Button>
			</CardContent>
		</Card>
	</div>
{:else if problem}
	<!-- Small, secondary control for re-running a generator after content exists -->
	{#snippet regenButton(action: () => void, busy: boolean)}
		<Button
			variant="ghost"
			size="sm"
			class="h-7 gap-1.5 px-2.5 text-[11px] font-semibold text-slate-500 hover:text-blue-600"
			onclick={action}
			disabled={busy}
			aria-label="Regenerate"
		>
			<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" class="h-3.5 w-3.5 {busy ? 'animate-spin' : ''}">
				<path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
			</svg>
			{busy ? 'Regenerating…' : 'Regenerate'}
		</Button>
	{/snippet}

	<div class="flex flex-col gap-4 h-[calc(100vh-theme(spacing.16)-4rem)]">
		<!-- Breadcrumb -->
		<nav class="flex items-center gap-1.5 text-xs font-medium text-slate-500" aria-label="Breadcrumb">
			<a href="/problems" class="rounded text-slate-500 transition-colors hover:text-blue-600">Problems</a>
			<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="h-3.5 w-3.5 text-slate-300" aria-hidden="true">
				<path fill-rule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clip-rule="evenodd" />
			</svg>
			<span class="truncate font-semibold text-slate-700" aria-current="page">{problem.title}</span>
		</nav>

		<div class="grid min-h-0 flex-1 grid-cols-1 gap-6 lg:grid-cols-5">
			<!-- Left Side: Problem Statement (40%) -->
		<Card class="lg:col-span-2 flex flex-col h-full overflow-y-auto border-slate-200 bg-white p-6 gap-4">
			<div class="flex justify-between items-center">
				<DifficultyBadge difficulty={problem.difficulty} />
				<div class="flex items-center gap-3">
					{#if problem.leetcode_url}
						<a href={problem.leetcode_url} target="_blank" rel="noreferrer" class="text-xs text-blue-600 hover:text-blue-700 font-semibold hover:underline">
							Official LeetCode ↗
						</a>
					{/if}
					<button
						onclick={toggleBookmark}
						title={isBookmarked ? 'Remove bookmark' : 'Bookmark this problem'}
						class="text-xl leading-none transition-all duration-150 hover:scale-110 {isBookmarked ? 'text-amber-500' : 'text-slate-300 hover:text-amber-400'}"
					>
						{isBookmarked ? '★' : '☆'}
					</button>
				</div>
			</div>

			<h2 class="font-title text-xl font-bold text-slate-900">{problem.title}</h2>

			<div class="flex flex-col gap-5">
				<p class="text-[14.5px] text-slate-700 leading-relaxed white-space-pre-wrap">{problem.description}</p>

				{#if problem.examples && problem.examples.length > 0}
					<div class="flex flex-col gap-3">
						<h3 class="text-[14px] font-bold text-slate-800">Examples</h3>
						{#each problem.examples as example, i}
							<div class="bg-slate-50 border border-slate-200/60 rounded-xl p-4 flex flex-col gap-1.5">
								<span class="text-xs font-bold text-slate-500">Example {i + 1}:</span>
								<pre class="font-mono text-xs whitespace-pre-wrap text-slate-800"><strong>Input:</strong> {example.input || ''}</pre>
								<pre class="font-mono text-xs whitespace-pre-wrap text-slate-800"><strong>Output:</strong> {example.output || ''}</pre>
								{#if example.explanation}
									<p class="text-xs text-slate-500 mt-1.5 leading-relaxed"><strong>Explanation:</strong> {example.explanation}</p>
								{/if}
							</div>
						{/each}
					</div>
				{/if}

				{#if problem.constraints_text}
					<div class="flex flex-col gap-2">
						<h3 class="text-[14px] font-bold text-slate-800">Constraints</h3>
						<pre class="font-mono text-xs whitespace-pre-wrap text-slate-700 bg-slate-50 border border-slate-200/60 p-4 rounded-xl leading-relaxed">{problem.constraints_text}</pre>
					</div>
				{/if}

				<div class="flex flex-col gap-2 border-t border-slate-100 pt-4">
					<h3 class="text-[14px] font-bold text-slate-800">Your Confidence</h3>
					<div class="flex gap-1.5">
						{#each [1, 2, 3, 4, 5] as level}
							<button
								onclick={() => setConfidence(level)}
								class="w-9 h-9 rounded-lg border-2 text-sm font-bold transition-all duration-150 {confidence !== null && level <= confidence ? 'border-blue-600 bg-blue-50 text-blue-700' : 'border-slate-200 text-slate-400 hover:border-slate-300'}"
							>
								{level}
							</button>
						{/each}
					</div>
					<p class="text-[11px] text-slate-400">1 = need to relearn · 5 = could solve it in an interview</p>
				</div>
			</div>
		</Card>

		<!-- Right Side: Learning Tabs (60%) -->
		<Card class="lg:col-span-3 flex flex-col h-full overflow-y-auto border-slate-200 bg-white p-0">
			<Tabs.Root bind:value={activeTab} class="w-full flex flex-col h-full">
				<Tabs.List class="grid grid-cols-6 bg-slate-50 border-b border-slate-200 rounded-none h-12 p-0">
					<Tabs.Trigger value="logic" class="h-full rounded-none border-b-2 border-transparent data-[state=active]:border-blue-600 data-[state=active]:text-blue-600 font-semibold text-xs transition-all duration-200">
						Logic
					</Tabs.Trigger>
					<Tabs.Trigger value="pseudocode" class="h-full rounded-none border-b-2 border-transparent data-[state=active]:border-blue-600 data-[state=active]:text-blue-600 font-semibold text-xs transition-all duration-200">
						Pseudocode
					</Tabs.Trigger>
					<Tabs.Trigger value="animation" class="h-full rounded-none border-b-2 border-transparent data-[state=active]:border-blue-600 data-[state=active]:text-blue-600 font-semibold text-xs transition-all duration-200">
						Animation
					</Tabs.Trigger>
					<Tabs.Trigger value="code" class="h-full rounded-none border-b-2 border-transparent data-[state=active]:border-blue-600 data-[state=active]:text-blue-600 font-semibold text-xs transition-all duration-200">
						Code Editor
					</Tabs.Trigger>
					<Tabs.Trigger value="review" class="h-full rounded-none border-b-2 border-transparent data-[state=active]:border-blue-600 data-[state=active]:text-blue-600 font-semibold text-xs transition-all duration-200">
						AI Review
					</Tabs.Trigger>
					<Tabs.Trigger value="notes" class="h-full rounded-none border-b-2 border-transparent data-[state=active]:border-blue-600 data-[state=active]:text-blue-600 font-semibold text-xs transition-all duration-200">
						Notes
					</Tabs.Trigger>
				</Tabs.List>

				<!-- Tab 1: Logic -->
				<Tabs.Content value="logic" class="flex-1 flex flex-col p-6 m-0 outline-none">
					{#if isGeneratingExplanation && !aiExplanation}
						<!-- Skeleton while the explanation generates -->
						<div class="flex flex-col gap-5">
							<div class="flex flex-col gap-2">
								<Skeleton class="h-4 w-24" />
								<Skeleton class="h-20 w-full rounded-xl" />
							</div>
							<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
								<div class="flex flex-col gap-2"><Skeleton class="h-3 w-20" /><Skeleton class="h-24 w-full rounded-xl" /></div>
								<div class="flex flex-col gap-2"><Skeleton class="h-3 w-28" /><Skeleton class="h-24 w-full rounded-xl" /></div>
							</div>
							<div class="flex gap-6 py-3"><Skeleton class="h-6 w-36 rounded-full" /><Skeleton class="h-6 w-36 rounded-full" /></div>
						</div>
					{:else if aiExplanation}
						<div class="flex flex-col gap-5">
							<div class="flex items-center justify-between">
								<h3 class="font-title text-base font-bold text-slate-900">AI Explanation</h3>
								{@render regenButton(handleGenerateExplanation, isGeneratingExplanation)}
							</div>
							<div class="flex flex-col gap-1.5">
								<h4 class="text-sm font-bold text-slate-900">Core Idea</h4>
								<p class="text-xs text-slate-600 leading-relaxed bg-slate-50 border border-slate-100 p-4 rounded-xl">{aiExplanation.simple_explanation}</p>
							</div>

							<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
								<div class="flex flex-col gap-1.5">
									<h4 class="text-xs font-bold text-slate-900">Brute Force</h4>
									<p class="text-xs text-slate-600 leading-relaxed bg-slate-50 border border-slate-100 p-4 rounded-xl">{aiExplanation.brute_force}</p>
								</div>
								<div class="flex flex-col gap-1.5">
									<h4 class="text-xs font-bold text-slate-900">Optimized Approach</h4>
									<p class="text-xs text-slate-600 leading-relaxed bg-slate-50 border border-slate-100 p-4 rounded-xl">{aiExplanation.optimized_approach}</p>
								</div>
							</div>

							<div class="flex gap-6 mt-2 border-t border-b border-slate-100 py-3 text-xs">
								<div class="flex items-center gap-2">
									<span class="font-semibold text-slate-500">Time Complexity:</span>
									<Badge class="bg-blue-50 text-blue-700 border border-blue-200/50 hover:bg-blue-50 font-bold px-2.5 py-0.5 rounded-full transition-all {focusedComplexity === 'time' ? 'ring-2 ring-amber-400/70 scale-105' : ''}">{aiExplanation.time_complexity}</Badge>
								</div>
								<div class="flex items-center gap-2">
									<span class="font-semibold text-slate-500">Space Complexity:</span>
									<Badge class="bg-blue-50 text-blue-700 border border-blue-200/50 hover:bg-blue-50 font-bold px-2.5 py-0.5 rounded-full transition-all {focusedComplexity === 'space' ? 'ring-2 ring-amber-400/70 scale-105' : ''}">{aiExplanation.space_complexity}</Badge>
								</div>
							</div>

							{#if aiExplanation.common_mistakes && aiExplanation.common_mistakes.length > 0}
								<div class="flex flex-col gap-2">
									<h4 class="text-xs font-bold text-slate-900">Common Mistakes</h4>
									<ul class="list-disc pl-5 text-xs text-slate-600 leading-relaxed flex flex-col gap-1">
										{#each aiExplanation.common_mistakes as mistake}
											<li>{mistake}</li>
										{/each}
									</ul>
								</div>
							{/if}
						</div>
					{:else}
						<!-- Honest error: never fabricate explanation content -->
						<div class="flex flex-col items-center justify-center text-center gap-3 max-w-[360px] m-auto">
							<h3 class="font-title text-base font-bold text-slate-900">Couldn't generate explanation</h3>
							<p class="text-xs text-slate-500 leading-relaxed">{explanationError || 'No AI explanation is available yet for this problem.'}</p>
							<Button class="bg-blue-600 hover:bg-blue-700 text-white w-full h-10 text-xs" onclick={handleGenerateExplanation} disabled={isGeneratingExplanation}>
								{#if isGeneratingExplanation}Generating…{:else}Try again{/if}
							</Button>
						</div>
					{/if}
				</Tabs.Content>

				<!-- Tab 2: Pseudocode -->
				<Tabs.Content value="pseudocode" class="flex-1 flex flex-col p-6 m-0 outline-none h-full">
					{#if isGeneratingExplanation && !aiExplanation}
						<!-- Skeleton while the explanation (which carries pseudocode) generates -->
						<div class="flex flex-col gap-2 flex-1">
							<Skeleton class="h-4 w-40" />
							<div class="flex flex-col gap-2 rounded-xl border border-slate-200 p-4 flex-1">
								{#each Array(8) as _, i}
									<Skeleton class="h-3.5" style="width: {[70, 85, 55, 90, 60, 80, 50, 75][i]}%" />
								{/each}
							</div>
						</div>
					{:else if aiExplanation}
						<div class="flex flex-col border border-slate-200 rounded-xl overflow-hidden flex-1 h-full bg-slate-50/50">
							<div class="flex items-center justify-between bg-slate-50 border-b border-slate-200 px-4 py-1.5">
								<span class="font-bold text-[11px] text-slate-500 uppercase tracking-wider">Pseudocode Template</span>
								{@render regenButton(handleGenerateExplanation, isGeneratingExplanation)}
							</div>
							<div class="flex flex-col font-mono text-[12.5px] py-2 overflow-y-auto bg-white flex-1 leading-relaxed">
								{#each aiExplanation.pseudocode as line, index}
									{@const isHighlighted = activeStep?.pseudocode_line === (index + 1)}
									<div class="flex py-1.5 transition-all duration-200 border-l-3 {isHighlighted ? 'bg-amber-50/70 border-amber-500' : 'border-transparent'}">
										<span class="w-12 text-right pr-4 text-slate-400 select-none font-bold text-[11px]">{index + 1}</span>
										<span class="text-slate-800 whitespace-pre-wrap">{line}</span>
									</div>
								{/each}
							</div>
						</div>
					{:else}
						<!-- Honest error: pseudocode comes from the explanation generator -->
						<div class="flex flex-col items-center justify-center text-center gap-3 max-w-[360px] m-auto">
							<h3 class="font-title text-base font-bold text-slate-900">Couldn't load pseudocode</h3>
							<p class="text-xs text-slate-500 leading-relaxed">{explanationError || 'No pseudocode is available yet for this problem.'}</p>
							<Button class="bg-blue-600 hover:bg-blue-700 text-white w-full h-10 text-xs" onclick={handleGenerateExplanation} disabled={isGeneratingExplanation}>
								{#if isGeneratingExplanation}Generating…{:else}Try again{/if}
							</Button>
						</div>
					{/if}
				</Tabs.Content>

				<!-- Tab 3: Animation -->
				<Tabs.Content value="animation" class="flex-1 flex flex-col p-6 m-0 outline-none">
					{#if isGeneratingAnimation && !animationData}
						<!-- Skeleton while the animation steps generate -->
						<div class="flex flex-col gap-4 flex-1">
							<div class="flex items-center gap-2">
								<Skeleton class="h-8 w-20 rounded-lg" />
								<Skeleton class="h-8 w-24 rounded-lg" />
								<Skeleton class="h-8 w-20 rounded-lg" />
								<Skeleton class="ml-auto h-7 w-24 rounded-full" />
							</div>
							<Skeleton class="h-16 w-full rounded-xl" />
							<div class="flex flex-1 items-center justify-center gap-2 rounded-xl border border-slate-200 p-6">
								{#each Array(6) as _}
									<Skeleton class="h-14 w-14 rounded-xl" />
								{/each}
							</div>
						</div>
					{:else if animationData}
						<div class="flex flex-col gap-4 flex-1">
							<!-- Player Controls -->
							<div class="flex items-center gap-2 flex-wrap">
								<Button variant="outline" size="sm" class="text-xs py-1 px-3 h-8 border-slate-200" onclick={stepPrev} disabled={currentStepIndex === 0}>◀ Prev</Button>
								<Button class="bg-blue-600 hover:bg-blue-700 text-white text-xs py-1 px-4 h-8 font-medium" onclick={togglePlay}>
									{isPlaying ? '⏸ Pause' : '▶ Play'}
								</Button>
								<Button variant="outline" size="sm" class="text-xs py-1 px-3 h-8 border-slate-200" onclick={stepNext} disabled={currentStepIndex === animationData.steps.length - 1}>Next ▶</Button>
								<Button variant="outline" size="sm" class="text-xs py-1 px-3 h-8 border-slate-200" onclick={resetAnimation}>Reset</Button>

								<span class="text-xs font-bold text-slate-500 ml-auto bg-slate-100 px-3 py-1 rounded-full">
									Step {currentStepIndex + 1} / {animationData.steps.length}
								</span>
								{@render regenButton(handleGenerateAnimation, isGeneratingAnimation)}
							</div>

							<!-- Scrubber + speed -->
							<div class="flex items-center gap-3">
								<input
									type="range"
									min="0"
									max={animationData.steps.length - 1}
									bind:value={currentStepIndex}
									aria-label="Animation timeline"
									aria-valuetext="Step {currentStepIndex + 1} of {animationData.steps.length}"
									class="h-2 flex-1 cursor-pointer accent-blue-600"
								/>
								<div class="flex items-center gap-0.5 rounded-lg border border-slate-200 bg-slate-50 p-0.5" role="group" aria-label="Playback speed">
									{#each [{ label: '0.5×', ms: 3000 }, { label: '1×', ms: 1500 }, { label: '2×', ms: 750 }] as opt}
										<button
											type="button"
											onclick={() => setSpeed(opt.ms)}
											aria-pressed={playbackSpeed === opt.ms}
											class="rounded-md px-2 py-1 text-[11px] font-bold transition-colors {playbackSpeed === opt.ms ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-500 hover:text-slate-800'}"
										>
											{opt.label}
										</button>
									{/each}
								</div>
							</div>

							<!-- Step Description -->
							<div class="bg-blue-50/50 border border-blue-100 rounded-xl p-4 text-xs text-slate-700 flex flex-col gap-1.5 leading-relaxed">
								<p><strong>Action:</strong> {animationData.steps[currentStepIndex]?.action}</p>
								<p><strong>Result:</strong> {animationData.steps[currentStepIndex]?.result}</p>
							</div>

							<!-- Visual Render Area -->
							<div class="border border-slate-200 rounded-xl bg-slate-50/50 p-6 flex-1 flex items-center justify-center">
								{#if animationData.animation_type === 'hash_map_array'}
									<div class="w-full flex flex-col gap-6">
										<div class="flex flex-col gap-2">
											<h4 class="text-xs font-bold text-slate-500 uppercase tracking-wider">Array Elements</h4>
											<div class="flex gap-2 flex-wrap">
												{#each animationData.input.array as num, i}
													{@const isCurrent = animationData.steps[currentStepIndex]?.index === i}
													<div class="w-14 h-14 bg-white border-2 rounded-xl flex flex-col items-center justify-center relative transition-all duration-200 {isCurrent ? 'border-blue-600 bg-blue-50/60 scale-105 shadow-md' : 'border-slate-200'}">
														<span class="text-[9px] font-bold text-slate-400 absolute top-1">{i}</span>
														<span class="text-base font-extrabold text-slate-900 mt-2 font-title">{num}</span>
													</div>
												{/each}
											</div>
										</div>

										<div class="flex flex-col gap-2">
											<h4 class="text-xs font-bold text-slate-500 uppercase tracking-wider">Hash Map State</h4>
											<div class="bg-white border border-slate-200 rounded-xl p-4 overflow-hidden">
												{#if Object.keys(animationData.steps[currentStepIndex]?.map || {}).length === 0}
													<p class="text-xs text-slate-400 text-center py-2 font-medium">Map is empty</p>
												{:else}
													<table class="w-full text-xs text-left border-collapse">
														<thead>
															<tr class="border-b border-slate-200">
																<th class="pb-2 text-slate-500 font-bold">Key (Value)</th>
																<th class="pb-2 text-slate-500 font-bold">Value (Index)</th>
															</tr>
														</thead>
														<tbody>
															{#each Object.entries(animationData.steps[currentStepIndex]?.map || {}) as [key, val]}
																<tr class="border-b border-slate-100 last:border-0">
																	<td class="py-2.5 font-bold text-slate-800">{key}</td>
																	<td class="py-2.5 font-semibold text-slate-600">{val}</td>
																</tr>
															{/each}
														</tbody>
													</table>
												{/if}
											</div>
										</div>
									</div>
								{:else if animationData.animation_type === 'two_pointers'}
									{@const step = animationData.steps[currentStepIndex]}
									<div class="w-full flex flex-col gap-4 items-center">
										<div class="flex gap-2 flex-wrap justify-center">
											{#each animationData.input.array as val, i}
												{@const isLeft = step?.left === i}
												{@const isRight = step?.right === i}
												{@const isFound = Array.isArray(step?.found) && step.found.includes(i)}
												<div class="flex flex-col items-center gap-1.5">
													<div class="w-14 h-14 bg-white border-2 rounded-xl flex flex-col items-center justify-center relative transition-all duration-200 {isFound ? 'border-emerald-500 bg-emerald-50 scale-105 shadow-md' : (isLeft || isRight) ? 'border-blue-600 bg-blue-50/60 scale-105 shadow-md' : 'border-slate-200'}">
														<span class="text-[9px] font-bold text-slate-400 absolute top-1">{i}</span>
														<span class="text-base font-extrabold text-slate-900 mt-2 font-title">{val}</span>
													</div>
													<span class="text-[10px] font-bold h-4 {isLeft ? 'text-blue-600' : isRight ? 'text-violet-600' : 'text-transparent'}">
														{isLeft && isRight ? '▲ L+R' : isLeft ? '▲ L' : isRight ? '▲ R' : '·'}
													</span>
												</div>
											{/each}
										</div>
									</div>
								{:else if animationData.animation_type === 'sliding_window'}
									{@const step = animationData.steps[currentStepIndex]}
									<div class="w-full flex flex-col gap-5 items-center">
										<div class="flex gap-2 flex-wrap justify-center">
											{#each animationData.input.array as val, i}
												{@const inWindow = step && i >= step.window_start && i <= step.window_end}
												<div class="w-14 h-14 bg-white border-2 rounded-xl flex flex-col items-center justify-center relative transition-all duration-200 {inWindow ? 'border-blue-600 bg-blue-50/60 shadow-md' : 'border-slate-200 opacity-60'}">
													<span class="text-[9px] font-bold text-slate-400 absolute top-1">{i}</span>
													<span class="text-base font-extrabold text-slate-900 mt-2 font-title">{val}</span>
												</div>
											{/each}
										</div>
										{#if step}
											<div class="text-xs font-semibold text-slate-600 bg-white border border-slate-200 rounded-full px-4 py-1.5">
												Window [{step.window_start} … {step.window_end}]{step.state ? ` — ${step.state}` : ''}
											</div>
										{/if}
									</div>
								{:else if animationData.animation_type === 'binary_search'}
									{@const step = animationData.steps[currentStepIndex]}
									<div class="w-full flex flex-col gap-4 items-center">
										<div class="flex gap-2 flex-wrap justify-center">
											{#each animationData.input.array as val, i}
												{@const eliminated = Array.isArray(step?.eliminated) && step.eliminated.includes(i)}
												{@const isMid = step?.mid === i}
												{@const isFound = step?.found === i}
												<div class="flex flex-col items-center gap-1.5">
													<div class="w-14 h-14 border-2 rounded-xl flex flex-col items-center justify-center relative transition-all duration-200 {isFound ? 'border-emerald-500 bg-emerald-50 scale-105 shadow-md' : isMid ? 'border-amber-500 bg-amber-50 scale-105 shadow-md' : eliminated ? 'border-slate-100 bg-slate-100 opacity-40' : 'border-slate-200 bg-white'}">
														<span class="text-[9px] font-bold text-slate-400 absolute top-1">{i}</span>
														<span class="text-base font-extrabold text-slate-900 mt-2 font-title">{val}</span>
													</div>
													<span class="text-[10px] font-bold h-4 {(step?.low === i || step?.high === i || isMid) ? 'text-slate-600' : 'text-transparent'}">
														{[step?.low === i ? 'lo' : '', isMid ? 'mid' : '', step?.high === i ? 'hi' : ''].filter(Boolean).join('·') || '·'}
													</span>
												</div>
											{/each}
										</div>
										{#if animationData.input.target !== undefined && animationData.input.target !== null}
											<div class="text-xs font-semibold text-slate-600 bg-white border border-slate-200 rounded-full px-4 py-1.5">
												Target: {animationData.input.target}
											</div>
										{/if}
									</div>
								{:else if animationData.animation_type === 'stack'}
									{@const step = animationData.steps[currentStepIndex]}
									<div class="w-full grid grid-cols-1 md:grid-cols-2 gap-8">
										<div class="flex flex-col gap-2">
											<h4 class="text-xs font-bold text-slate-500 uppercase tracking-wider">Input</h4>
											<div class="flex gap-1.5 flex-wrap">
												{#each animationData.input.array as ch, i}
													{@const isCursor = step?.cursor === i}
													<div class="w-10 h-10 bg-white border-2 rounded-lg flex items-center justify-center font-mono font-bold text-sm transition-all duration-200 {isCursor ? 'border-blue-600 bg-blue-50/60 scale-110 shadow-md' : i < (step?.cursor ?? -1) ? 'border-slate-100 opacity-40' : 'border-slate-200'}">{ch}</div>
												{/each}
											</div>
											{#if step?.op}
												<div class="mt-2 text-xs font-bold {step.op === 'push' ? 'text-emerald-600' : step.op === 'pop' ? 'text-rose-600' : 'text-slate-500'}">
													{String(step.op).toUpperCase()}{step.value !== undefined && step.value !== null ? ` → ${step.value}` : ''}
												</div>
											{/if}
										</div>
										<div class="flex flex-col gap-2">
											<h4 class="text-xs font-bold text-slate-500 uppercase tracking-wider">Stack (top at the top)</h4>
											<div class="flex flex-col-reverse gap-1.5 min-h-[140px] w-28 border-2 border-t-0 border-slate-300 rounded-b-xl p-3 justify-start">
												{#each step?.stack ?? [] as item}
													<div class="h-9 bg-blue-50 border border-blue-200 rounded-md flex items-center justify-center font-mono font-bold text-sm text-blue-700">{item}</div>
												{/each}
												{#if !step?.stack?.length}
													<span class="text-[10px] text-slate-400 text-center m-auto">empty</span>
												{/if}
											</div>
										</div>
									</div>
								{:else}
									<div class="text-center text-xs text-slate-500 flex flex-col gap-1.5">
										<p>Visualizing animation type: <strong>{animationData.animation_type}</strong></p>
										<p>Inputs: {JSON.stringify(animationData.input)}</p>
										<p>Step Variables: {JSON.stringify(animationData.steps[currentStepIndex])}</p>
									</div>
								{/if}
							</div>
						</div>
					{:else}
						<!-- Honest error: never fabricate animation steps -->
						<div class="flex flex-col items-center justify-center text-center gap-3 max-w-[360px] m-auto">
							<h3 class="font-title text-base font-bold text-slate-900">Couldn't generate animation</h3>
							<p class="text-xs text-slate-500 leading-relaxed">{animationError || 'No animation is available yet for this problem.'}</p>
							<Button class="bg-blue-600 hover:bg-blue-700 text-white w-full h-10 text-xs" onclick={handleGenerateAnimation} disabled={isGeneratingAnimation}>
								{#if isGeneratingAnimation}Generating…{:else}Try again{/if}
							</Button>
						</div>
					{/if}
				</Tabs.Content>

				<!-- Tab 4: Code Editor -->
				<Tabs.Content value="code" class="flex-1 flex flex-col p-0 m-0 outline-none h-full bg-slate-950">
					<div class="bg-slate-900 border-b border-slate-800 px-4 py-2.5 text-[11px] font-bold text-slate-400 uppercase tracking-wider">
						Python Sandbox (Python 3)
					</div>
					<textarea aria-label="Python code editor" class="w-full flex-1 bg-slate-950 text-slate-100 font-mono text-[13px] p-5 outline-none resize-none leading-relaxed focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-blue-500/50" bind:value={submittedCode} spellcheck="false"></textarea>

					<!-- Editor Buttons -->
					<div class="flex items-center justify-between p-4 bg-slate-900 border-t border-slate-800">
						<div class="flex gap-2">
							<Button variant="outline" size="sm" class="text-[11px] h-8 border-slate-800 text-slate-300 hover:text-white hover:bg-slate-800 bg-transparent" onclick={() => handleGetHint(1)}>Hint L1</Button>
							<Button variant="outline" size="sm" class="text-[11px] h-8 border-slate-800 text-slate-300 hover:text-white hover:bg-slate-800 bg-transparent" onclick={() => handleGetHint(2)}>Hint L2</Button>
							<Button variant="outline" size="sm" class="text-[11px] h-8 border-slate-800 text-slate-300 hover:text-white hover:bg-slate-800 bg-transparent" onclick={() => handleGetHint(3)}>Hint L3</Button>
						</div>

						<Button class="bg-blue-600 hover:bg-blue-700 text-white text-xs h-8 px-4 font-semibold" onclick={handleReviewCode} disabled={isSubmittingCode}>
							{#if isSubmittingCode}Analyzing with AI...{:else}Review with AI{/if}
						</Button>
					</div>

					<!-- Hint Banner -->
					{#if hintText}
						<div class="bg-amber-950/40 border-t border-amber-900/30 p-4 text-xs text-amber-200 leading-relaxed">
							<span class="font-bold text-amber-400 block mb-1">💡 Hint Level {activeHintLevel}:</span>
							<p>{hintText}</p>
						</div>
					{/if}
				</Tabs.Content>

				<!-- Tab 5: AI Review -->
				<Tabs.Content value="review" class="flex-1 flex flex-col p-6 m-0 outline-none">
					{#if isSubmittingCode}
						<LoadingState message="Gemini is reviewing your solution…" class="m-auto" />
					{:else if !codeReview}
						<div class="flex flex-col items-center justify-center text-center gap-2 max-w-[340px] m-auto">
							<h3 class="font-title text-base font-bold text-slate-900">AI Code Reviews</h3>
							<p class="text-xs text-slate-500 leading-relaxed">
								Submit your code solution in the Code Editor tab to trigger an instant AI review on correctness, time/space complexities, and bugs.
							</p>
							{#if aiError}
								<p class="text-xs text-rose-600 bg-rose-50 border border-rose-200 rounded-lg p-3 leading-relaxed mt-2">{aiError}</p>
							{/if}
						</div>
					{:else}
						<div class="flex flex-col gap-5">
							<div class="grid grid-cols-2 gap-4">
								<Card class="bg-slate-50 border border-slate-200/60 p-4 flex flex-col gap-1">
									<span class="text-[11px] font-bold text-slate-400 uppercase tracking-wider">AI Review Score</span>
									<span class="text-2xl font-extrabold text-blue-600 font-title">{codeReview.score}%</span>
								</Card>
								<Card class="bg-slate-50 border border-slate-200/60 p-4 flex flex-col gap-1">
									<span class="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Correctness Status</span>
									<span class="text-2xl font-extrabold font-title {codeReview.is_correct ? 'text-emerald-600' : 'text-rose-600'}">
										{codeReview.is_correct ? 'Correct' : 'Needs Fix'}
									</span>
								</Card>
							</div>

							<div class="flex flex-col gap-1.5">
								<h4 class="text-xs font-bold text-slate-900 uppercase tracking-wider">Logic Feedback</h4>
								<p class="text-xs text-slate-600 leading-relaxed bg-slate-50 border border-slate-100 p-4 rounded-xl">{codeReview.logic_feedback}</p>
							</div>

							<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
								<div class="flex flex-col gap-2 bg-slate-50/50 border border-slate-100 p-4 rounded-xl">
									<h4 class="text-xs font-bold text-slate-800">Detected Bugs</h4>
									{#if codeReview.bugs.length === 0}
										<p class="text-xs text-slate-500 font-medium">No critical syntax bugs detected.</p>
									{:else}
										<ul class="list-disc pl-5 text-xs text-rose-600 flex flex-col gap-1 leading-relaxed">
											{#each codeReview.bugs as bug}
												<li>{bug}</li>
											{/each}
										</ul>
									{/if}
								</div>

								<div class="flex flex-col gap-2 bg-slate-50/50 border border-slate-100 p-4 rounded-xl">
									<h4 class="text-xs font-bold text-slate-800">Missed Edge Cases</h4>
									{#if codeReview.missed_edge_cases.length === 0}
										<p class="text-xs text-slate-500 font-medium">Excellent handling of edge scenarios.</p>
									{:else}
										<ul class="list-disc pl-5 text-xs text-amber-600 flex flex-col gap-1 leading-relaxed">
											{#each codeReview.missed_edge_cases as edge}
												<li>{edge}</li>
											{/each}
										</ul>
									{/if}
								</div>
							</div>

							<div class="flex flex-col gap-1.5">
								<h4 class="text-xs font-bold text-slate-900 uppercase tracking-wider">Recommended Better Approach</h4>
								<p class="text-xs text-slate-600 leading-relaxed bg-slate-50 border border-slate-100 p-4 rounded-xl">{codeReview.better_approach}</p>
							</div>
						</div>
					{/if}
				</Tabs.Content>

				<!-- Tab 6: Notes -->
				<Tabs.Content value="notes" class="flex-1 flex flex-col p-6 m-0 outline-none gap-3">
					<div class="flex items-center justify-between">
						<div>
							<h3 class="text-sm font-bold text-slate-900">My Notes</h3>
							<p class="text-[11px] text-slate-400 mt-0.5">Mistakes you made, the key insight, patterns to remember.</p>
						</div>
						<div class="flex items-center gap-2">
							{#if noteStatus === 'saved'}
								<span class="text-[11px] font-semibold text-emerald-600">Saved ✓</span>
							{:else if noteStatus === 'error'}
								<span class="text-[11px] font-semibold text-rose-600">Save failed</span>
							{/if}
							<Button class="bg-blue-600 hover:bg-blue-700 text-white text-xs h-8 px-4 font-semibold" onclick={saveNote} disabled={noteStatus === 'saving'}>
								{noteStatus === 'saving' ? 'Saving...' : 'Save Note'}
							</Button>
						</div>
					</div>
					<textarea
						bind:value={noteContent}
						aria-label="My notes for this problem"
						placeholder="e.g. I forgot the empty-array edge case. Key insight: the array being sorted means a too-small sum can only be fixed by moving the left pointer..."
						class="flex-1 w-full border border-slate-200 rounded-xl p-4 text-[13px] leading-relaxed text-slate-800 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-500/20 resize-none bg-slate-50/50 transition-all"
						spellcheck="false"
					></textarea>
				</Tabs.Content>
			</Tabs.Root>
		</Card>
		</div>
	</div>
{/if}
