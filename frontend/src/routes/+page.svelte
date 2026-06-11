<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';

	onMount(() => {
		const token = localStorage.getItem('token');
		if (token) {
			goto('/dashboard');
		} else {
			goto('/login');
		}
	});
</script>

<div class="redirecting">
	<div class="spinner"></div>
	<p>Redirecting to AlgoLens AI...</p>
</div>

<style>
	.redirecting {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		height: 100vh;
		background-color: var(--background);
		gap: 1rem;
	}
	.spinner {
		border: 4px solid var(--border);
		border-top: 4px solid var(--primary);
		border-radius: 50%;
		width: 40px;
		height: 40px;
		animation: spin 1s linear infinite;
	}
	@keyframes spin {
		to { transform: rotate(360deg); }
	}
</style>
