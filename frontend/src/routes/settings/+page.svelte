<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '$lib/components/ui/card';
	import { Input } from '$lib/components/ui/input';
	import { Label } from '$lib/components/ui/label';
	import { Button } from '$lib/components/ui/button';

	let fullName = $state('');
	let email = $state('');
	let leetcodeUsername = $state('');
	let isSaving = $state(false);
	let successMessage = $state('');
	let token = $state('');

	onMount(() => {
		const storedToken = localStorage.getItem('token');
		const storedUser = localStorage.getItem('user');
		if (!storedToken || !storedUser) {
			goto('/login');
			return;
		}
		token = storedToken;
		try {
			const user = JSON.parse(storedUser);
			fullName = user.full_name || '';
			email = user.email || '';
			leetcodeUsername = user.leetcode_username || '';
		} catch (e) {
			console.error(e);
		}
	});

	async function handleSave(event: SubmitEvent) {
		event.preventDefault();
		isSaving = true;
		successMessage = '';

		setTimeout(() => {
			const storedUser = localStorage.getItem('user');
			if (storedUser) {
				try {
					const user = JSON.parse(storedUser);
					user.full_name = fullName;
					user.leetcode_username = leetcodeUsername;
					localStorage.setItem('user', JSON.stringify(user));
					successMessage = 'Settings saved successfully!';
				} catch (e) {
					console.error(e);
				}
			}
			isSaving = false;
		}, 1000);
	}
</script>

<div class="flex flex-col gap-6 max-w-[600px] mx-auto w-full">
	<Card class="border-slate-200 bg-white p-6">
		<CardHeader class="p-0">
			<CardTitle class="text-lg font-bold text-slate-900">Account Settings</CardTitle>
			<CardDescription class="text-xs text-slate-500">
				Manage your AlgoLens AI profile preferences and sync integrations.
			</CardDescription>
		</CardHeader>
	</Card>

	<Card class="border-slate-200 bg-white p-8">
		<form onsubmit={handleSave} class="flex flex-col gap-5">
			{#if successMessage}
				<div class="bg-emerald-50 border border-emerald-100 text-emerald-600 text-xs rounded-lg p-3 font-medium">
					{successMessage}
				</div>
			{/if}

			<div class="flex flex-col gap-1.5">
				<Label for="fullName" class="text-slate-600">Full Name</Label>
				<Input type="text" id="fullName" bind:value={fullName} required class="h-10 border-slate-200 bg-white" />
			</div>

			<div class="flex flex-col gap-1.5">
				<Label for="email" class="text-slate-600">Email Address</Label>
				<Input type="email" id="email" bind:value={email} readonly class="h-10 border-slate-200 bg-slate-50 text-slate-500 cursor-not-allowed" />
				<span class="text-[10px] text-slate-400">Email address cannot be changed.</span>
			</div>

			<div class="flex flex-col gap-1.5">
				<Label for="lcUser" class="text-slate-600">LeetCode Username</Label>
				<Input type="text" id="lcUser" bind:value={leetcodeUsername} placeholder="e.g. leetcode_ninja" class="h-10 border-slate-200 bg-white" />
				<span class="text-[10px] text-slate-400">Used to sync solved counts and import history in later updates.</span>
			</div>

			<Button type="submit" class="w-fit h-10 px-6 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold" disabled={isSaving}>
				{#if isSaving}Saving...{:else}Save Changes{/if}
			</Button>
		</form>
	</Card>
</div>
