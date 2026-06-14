import { sveltekit } from '@sveltejs/kit/vite';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [tailwindcss(), sveltekit()],
	server: {
		watch: {
			// Playwright writes artifacts mid-run; reloading on them detaches
			// the DOM under test
			ignored: ['**/test-results/**', '**/playwright-report/**', '**/e2e/**']
		}
	}
});
