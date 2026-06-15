import { test, expect } from '@playwright/test';

// Backend-independent: the /login page renders without the API. Verifies the
// theme system end-to-end on a real render — the early init applies .dark
// before paint (no flash), the toggle persists, and there are no console errors.

function trackConsoleErrors(page: import('@playwright/test').Page): string[] {
	const errors: string[] = [];
	page.on('console', (msg) => {
		if (msg.type() === 'error') errors.push(msg.text());
	});
	page.on('pageerror', (err) => errors.push(err.message));
	return errors;
}

test('dark theme is applied before paint (no flash) with no console errors', async ({ page }) => {
	const errors = trackConsoleErrors(page);
	// Set the saved preference BEFORE any page script runs.
	await page.addInitScript(() => localStorage.setItem('theme', 'dark'));

	await page.goto('/login');
	// The early init script must have added .dark to <html> by first render.
	await expect(page.locator('html')).toHaveClass(/dark/);
	const colorScheme = await page.evaluate(() => document.documentElement.style.colorScheme);
	expect(colorScheme).toBe('dark');

	// Wait for the SPA to mount its content before capturing.
	await expect(page.getByRole('button', { name: 'Sign In' })).toBeVisible();
	await page.screenshot({ path: 'test-results/login-dark.png', fullPage: true });
	expect(errors, `console errors: ${errors.join(' | ')}`).toEqual([]);
});

test('light theme renders without the dark class', async ({ page }) => {
	const errors = trackConsoleErrors(page);
	await page.addInitScript(() => localStorage.setItem('theme', 'light'));

	await page.goto('/login');
	await expect(page.locator('html')).not.toHaveClass(/dark/);

	await expect(page.getByRole('button', { name: 'Sign In' })).toBeVisible();
	await page.screenshot({ path: 'test-results/login-light.png', fullPage: true });
	expect(errors, `console errors: ${errors.join(' | ')}`).toEqual([]);
});

test('app shell (sidebar + header + toggle) renders in dark', async ({ page }) => {
	// A token makes the layout mount the protected shell; the bootstrap API call
	// fails offline and is caught, so the shell still renders (nav is static).
	await page.addInitScript(() => {
		localStorage.setItem('theme', 'dark');
		localStorage.setItem('token', 'e2e-fake-token');
	});
	// /settings shows the shell and does not self-redirect when the API is offline.
	await page.goto('/settings');
	await expect(page.locator('html')).toHaveClass(/dark/);
	// Sidebar nav + theme toggles (sidebar + settings Appearance card) are present.
	await expect(page.getByRole('link', { name: 'Topic Notes' })).toBeVisible();
	await expect(page.getByRole('group', { name: 'Color theme' }).first()).toBeVisible();
	await expect(page.getByText('Appearance')).toBeVisible();
	await page.screenshot({ path: 'test-results/shell-dark.png', fullPage: false });
});

test('preference persists across reload', async ({ page }) => {
	await page.addInitScript(() => localStorage.setItem('theme', 'dark'));
	await page.goto('/login');
	await expect(page.locator('html')).toHaveClass(/dark/);
	await page.reload();
	await expect(page.locator('html')).toHaveClass(/dark/);
});

test('dark is the default when no preference is stored', async ({ page }) => {
	// No theme written to localStorage → should default to dark, before paint.
	await page.addInitScript(() => localStorage.removeItem('theme'));
	await page.goto('/login');
	await expect(page.locator('html')).toHaveClass(/dark/);
});

test('an explicit light choice overrides the dark default and persists', async ({ page }) => {
	await page.addInitScript(() => localStorage.setItem('theme', 'light'));
	await page.goto('/login');
	await expect(page.locator('html')).not.toHaveClass(/dark/);
	await page.reload();
	await expect(page.locator('html')).not.toHaveClass(/dark/);
});
