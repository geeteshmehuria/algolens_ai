import { test, expect } from '@playwright/test';

// Guards Phase 6: a logged-out user hitting a protected route must be redirected
// to /login WITHOUT the protected shell/content ever rendering (no "flash").
// Backend-independent: the redirect is a purely client-side gate in +layout.svelte.

test.describe('auth no-flash', () => {
	test.beforeEach(async ({ page }) => {
		// Ensure no session before the app boots.
		await page.addInitScript(() => {
			localStorage.removeItem('token');
			localStorage.removeItem('user');
		});
	});

	test('direct /dashboard while logged out redirects to /login with no dashboard content', async ({
		page
	}) => {
		await page.goto('/dashboard');
		await page.waitForURL('**/login');

		// Dashboard-only markers must never appear at any point.
		await expect(page.getByText(/snapshot of your progress/i)).toHaveCount(0);
		await expect(page.getByText('Recommended Next Problems')).toHaveCount(0);

		// The login form is what should be visible instead.
		await expect(page.getByRole('button', { name: /sign in/i })).toBeVisible();
	});

	test('direct /problems while logged out redirects to /login', async ({ page }) => {
		await page.goto('/problems');
		await page.waitForURL('**/login');
		await expect(page.getByRole('button', { name: /sign in/i })).toBeVisible();
	});
});
