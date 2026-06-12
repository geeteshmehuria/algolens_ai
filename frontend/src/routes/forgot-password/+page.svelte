<script lang="ts">
	import { api } from '$lib/api';
	import { Button } from '$lib/components/ui/button';
	import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '$lib/components/ui/card';
	import { Input } from '$lib/components/ui/input';
	import { Label } from '$lib/components/ui/label';

	let email = $state('');
	let submitted = $state(false);
	let errorMessage = $state('');
	let isLoading = $state(false);

	async function handleSubmit(event: SubmitEvent) {
		event.preventDefault();
		errorMessage = '';
		isLoading = true;

		try {
			await api('/auth/forgot-password', {
				method: 'POST',
				body: JSON.stringify({ email })
			});
			submitted = true;
		} catch (err: any) {
			errorMessage = err.message || 'Something went wrong. Please try again.';
		} finally {
			isLoading = false;
		}
	}
</script>

<div class="flex items-center justify-center min-h-screen bg-gradient-to-br from-slate-50 to-blue-50/50 p-4">
	<Card class="w-full max-w-[440px] shadow-xl border border-slate-200 bg-white">
		<CardHeader class="text-center pt-8 pb-4">
			<CardTitle class="text-2xl font-extrabold tracking-tight text-slate-900">
				Forgot Password
			</CardTitle>
			<CardDescription class="text-xs text-slate-500 mt-1">
				Enter your email and we'll send you a reset link
			</CardDescription>
		</CardHeader>

		<CardContent class="px-8 pb-8">
			{#if submitted}
				<div class="bg-emerald-50 border border-emerald-100 text-emerald-600 text-sm rounded-lg p-4 font-medium text-center">
					If an account exists for this email, a reset link has been sent.
					Please check your inbox.
				</div>
				<div class="text-center mt-4">
					<a href="/login" class="text-sm text-blue-600 hover:text-blue-700 font-medium">Back to login</a>
				</div>
			{:else}
				<form onsubmit={handleSubmit} class="flex flex-col gap-4">
					{#if errorMessage}
						<div class="bg-rose-50 border border-rose-100 text-rose-600 text-xs rounded-lg p-3 font-medium">
							{errorMessage}
						</div>
					{/if}

					<div class="flex flex-col gap-1.5">
						<Label for="email" class="text-slate-600">Email Address</Label>
						<Input type="email" id="email" bind:value={email} required placeholder="you@example.com" class="h-10 border-slate-200" />
					</div>

					<Button type="submit" class="w-full h-10 mt-2 bg-blue-600 hover:bg-blue-700 text-white font-medium" disabled={isLoading}>
						{#if isLoading}
							<div class="animate-spin rounded-full h-4 w-4 border-2 border-white/30 border-t-white mr-2"></div>
							Sending...
						{:else}
							Send Reset Link
						{/if}
					</Button>

					<div class="text-center">
						<a href="/login" class="text-sm text-slate-500 hover:text-slate-700">Back to login</a>
					</div>
				</form>
			{/if}
		</CardContent>
	</Card>
</div>
