<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { api } from '$lib/api';
	import { Button } from '$lib/components/ui/button';
	import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '$lib/components/ui/card';
	import { Input } from '$lib/components/ui/input';
	import { Label } from '$lib/components/ui/label';

	let isLogin = $state(true);
	let email = $state('');
	let password = $state('');
	let fullName = $state('');
	let errorMessage = $state('');
	let successMessage = $state('');
	let isLoading = $state(false);

	onMount(() => {
		if (localStorage.getItem('token')) {
			goto('/dashboard');
		}
		if (new URLSearchParams(window.location.search).get('reset') === 'success') {
			successMessage = 'Password reset successful! Please log in with your new password.';
		}
	});

	async function handleSubmit(event: SubmitEvent) {
		event.preventDefault();
		errorMessage = '';
		successMessage = '';
		isLoading = true;

		const payload = isLogin
			? { email, password }
			: { email, password, full_name: fullName };

		try {
			// No token in localStorage here, so api() sends no Authorization header
			const data = await api(isLogin ? '/auth/login' : '/auth/register', {
				method: 'POST',
				body: JSON.stringify(payload)
			});

			if (isLogin) {
				localStorage.setItem('token', data.access_token);
				try {
					const profileData = await api('/auth/me');
					localStorage.setItem('user', JSON.stringify(profileData));
				} catch {
					// profile fetch is best-effort — continue to dashboard without it
				}
				goto('/dashboard');
			} else {
				successMessage = 'Registration successful! Please log in.';
				isLogin = true;
				password = '';
			}
		} catch (err: any) {
			errorMessage = err.message || 'Something went wrong. Please try again.';
		} finally {
			isLoading = false;
		}
	}
</script>

<div class="grid min-h-screen lg:grid-cols-2">
	<!-- Brand panel (desktop only) -->
	<aside class="relative hidden flex-col justify-between overflow-hidden bg-slate-900 p-12 text-white lg:flex">
		<div class="absolute inset-0 bg-gradient-to-br from-blue-600/30 via-slate-900 to-slate-950"></div>
		<div class="absolute -right-24 -top-24 h-72 w-72 rounded-full bg-blue-500/20 blur-3xl"></div>
		<div class="absolute -bottom-24 -left-16 h-72 w-72 rounded-full bg-cyan-400/10 blur-3xl"></div>

		<div class="relative flex items-center gap-3">
			<div class="flex h-10 w-10 items-center justify-center rounded-lg bg-white/10 text-white ring-1 ring-white/20">
				<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="h-6 w-6">
					<path stroke-linecap="round" stroke-linejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12.9 19.5c-4.638 0-8.573-3.007-9.963-7.178z" />
					<path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
				</svg>
			</div>
			<span class="font-title text-lg font-bold">AlgoLens <span class="text-blue-400">AI</span></span>
		</div>

		<div class="relative max-w-md">
			<h2 class="font-title text-3xl font-bold leading-tight tracking-tight">
				Master Data Structures &amp; Algorithms, visually.
			</h2>
			<p class="mt-4 text-sm leading-relaxed text-slate-300">
				AI-generated notes, animated walkthroughs, spaced-repetition revision, and a
				personalized roadmap — all in one focused workspace.
			</p>
			<ul class="mt-8 flex flex-col gap-3 text-sm text-slate-200">
				<li class="flex items-center gap-3"><span class="text-blue-400">✓</span> Step-by-step algorithm animations</li>
				<li class="flex items-center gap-3"><span class="text-blue-400">✓</span> AI explanations &amp; complexity breakdowns</li>
				<li class="flex items-center gap-3"><span class="text-blue-400">✓</span> Smart revision that adapts to you</li>
			</ul>
		</div>

		<p class="relative text-xs text-slate-400">Built for focused, interview-ready learning.</p>
	</aside>

	<!-- Form panel -->
	<div class="flex items-center justify-center bg-gradient-to-br from-slate-50 to-blue-50/50 p-4">
	<Card class="w-full max-w-[440px] shadow-xl border border-slate-200 bg-white">
		<CardHeader class="text-center pt-8 pb-4">
			<div class="inline-flex w-12 h-12 bg-blue-50 text-blue-600 rounded-xl items-center justify-center mb-3 mx-auto lg:hidden">
				<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-7 h-7">
					<path stroke-linecap="round" stroke-linejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12.9 19.5c-4.638 0-8.573-3.007-9.963-7.178z" />
					<path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
				</svg>
			</div>
			<CardTitle class="font-title text-2xl font-extrabold tracking-tight text-slate-900">
				{isLogin ? 'Welcome back' : 'Create your account'}
			</CardTitle>
			<CardDescription class="text-xs text-slate-500 mt-1">
				{isLogin ? 'Sign in to continue your DSA journey' : 'Start learning DSA the visual way'}
			</CardDescription>
		</CardHeader>

		<CardContent class="px-8 pb-8">
			<!-- Tabs -->
			<div class="flex border-b border-slate-200 mb-6">
				<button type="button" class="flex-1 py-2.5 text-sm font-medium border-b-2 transition-all duration-200 text-center cursor-pointer {isLogin ? 'border-blue-600 text-blue-600 font-semibold' : 'border-transparent text-slate-500 hover:text-slate-900'}" onclick={() => { isLogin = true; errorMessage = ''; }}>
					Login
				</button>
				<button type="button" class="flex-1 py-2.5 text-sm font-medium border-b-2 transition-all duration-200 text-center cursor-pointer {!isLogin ? 'border-blue-600 text-blue-600 font-semibold' : 'border-transparent text-slate-500 hover:text-slate-900'}" onclick={() => { isLogin = false; errorMessage = ''; }}>
					Register
				</button>
			</div>

			<form onsubmit={handleSubmit} class="flex flex-col gap-4">
				{#if errorMessage}
					<div class="bg-rose-50 border border-rose-100 text-rose-600 text-xs rounded-lg p-3 font-medium">
						{errorMessage}
					</div>
				{/if}
				{#if successMessage}
					<div class="bg-emerald-50 border border-emerald-100 text-emerald-600 text-xs rounded-lg p-3 font-medium">
						{successMessage}
					</div>
				{/if}

				{#if !isLogin}
					<div class="flex flex-col gap-1.5">
						<Label for="fullName" class="text-slate-600">Full Name</Label>
						<Input type="text" id="fullName" bind:value={fullName} required placeholder="John Doe" class="h-10 border-slate-200" />
					</div>
				{/if}

				<div class="flex flex-col gap-1.5">
					<Label for="email" class="text-slate-600">Email Address</Label>
					<Input type="email" id="email" bind:value={email} required placeholder="you@example.com" class="h-10 border-slate-200" />
				</div>

				<div class="flex flex-col gap-1.5">
					<div class="flex items-center justify-between">
						<Label for="password" class="text-slate-600">Password</Label>
						{#if isLogin}
							<a href="/forgot-password" class="text-xs text-blue-600 hover:text-blue-700 font-medium">Forgot password?</a>
						{/if}
					</div>
					<Input type="password" id="password" bind:value={password} required placeholder="••••••••" class="h-10 border-slate-200" />
				</div>

				<Button type="submit" class="w-full h-10 mt-2 bg-blue-600 hover:bg-blue-700 text-white font-medium" disabled={isLoading}>
					{#if isLoading}
						<div class="animate-spin rounded-full h-4 w-4 border-2 border-white/30 border-t-white mr-2"></div>
						Processing...
					{:else}
						{isLogin ? 'Sign In' : 'Create Account'}
					{/if}
				</Button>
			</form>
		</CardContent>
	</Card>
	</div>
</div>
