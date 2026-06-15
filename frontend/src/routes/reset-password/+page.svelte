<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { api } from '$lib/api';
	import { Button } from '$lib/components/ui/button';
	import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '$lib/components/ui/card';
	import { Input } from '$lib/components/ui/input';
	import { Label } from '$lib/components/ui/label';

	let token = $state('');
	let newPassword = $state('');
	let confirmPassword = $state('');
	let errorMessage = $state('');
	let isLoading = $state(false);

	onMount(() => {
		token = new URLSearchParams(window.location.search).get('token') ?? '';
		if (!token) {
			errorMessage = 'This reset link is invalid. Please request a new one.';
		}
	});

	async function handleSubmit(event: SubmitEvent) {
		event.preventDefault();
		errorMessage = '';

		if (newPassword.length < 8) {
			errorMessage = 'Password must be at least 8 characters.';
			return;
		}
		if (newPassword !== confirmPassword) {
			errorMessage = 'Passwords do not match.';
			return;
		}

		isLoading = true;
		try {
			await api('/auth/reset-password', {
				method: 'POST',
				body: JSON.stringify({
					token,
					new_password: newPassword,
					confirm_password: confirmPassword
				})
			});
			goto('/login?reset=success');
		} catch (err: any) {
			errorMessage = err.message || 'Something went wrong. Please try again.';
		} finally {
			isLoading = false;
		}
	}
</script>

<div class="flex items-center justify-center min-h-screen bg-gradient-to-br from-slate-50 to-blue-50/50 dark:from-background dark:to-slate-900 p-4">
	<Card class="w-full max-w-[440px] shadow-xl border border-slate-200 bg-white">
		<CardHeader class="text-center pt-8 pb-4">
			<CardTitle class="text-2xl font-extrabold tracking-tight text-slate-900">
				Reset Password
			</CardTitle>
			<CardDescription class="text-xs text-slate-500 mt-1">
				Choose a new password for your account
			</CardDescription>
		</CardHeader>

		<CardContent class="px-8 pb-8">
			<form onsubmit={handleSubmit} class="flex flex-col gap-4">
				{#if errorMessage}
					<div class="bg-rose-50 border border-rose-100 text-rose-600 text-xs rounded-lg p-3 font-medium">
						{errorMessage}
					</div>
				{/if}

				<div class="flex flex-col gap-1.5">
					<Label for="newPassword" class="text-slate-600">New Password</Label>
					<Input type="password" id="newPassword" bind:value={newPassword} required minlength={8} placeholder="••••••••" class="h-10 border-slate-200" disabled={!token} />
				</div>

				<div class="flex flex-col gap-1.5">
					<Label for="confirmPassword" class="text-slate-600">Confirm Password</Label>
					<Input type="password" id="confirmPassword" bind:value={confirmPassword} required minlength={8} placeholder="••••••••" class="h-10 border-slate-200" disabled={!token} />
				</div>

				<Button type="submit" class="w-full h-10 mt-2 bg-blue-600 hover:bg-blue-700 text-white font-medium" disabled={isLoading || !token}>
					{#if isLoading}
						<div class="animate-spin rounded-full h-4 w-4 border-2 border-white/30 border-t-white mr-2"></div>
						Resetting...
					{:else}
						Reset Password
					{/if}
				</Button>

				<div class="text-center">
					<a href="/forgot-password" class="text-sm text-slate-500 hover:text-slate-700">Request a new link</a>
				</div>
			</form>
		</CardContent>
	</Card>
</div>
