import { defineConfig, devices } from '@playwright/test';

// E2E tests expect the backend API on :8000 (uvicorn) and will start the
// SvelteKit dev server on :5173 themselves if it isn't already running.
export default defineConfig({
	testDir: './e2e',
	fullyParallel: false,
	retries: 0,
	reporter: [['list']],
	use: {
		baseURL: 'http://localhost:5173',
		trace: 'retain-on-failure'
	},
	projects: [
		{
			name: 'chromium',
			use: { ...devices['Desktop Chrome'] }
		}
	],
	webServer: {
		command: 'pnpm dev',
		url: 'http://localhost:5173',
		reuseExistingServer: true,
		timeout: 60_000
	}
});
