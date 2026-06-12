import { test, expect, type Page } from '@playwright/test';
import { readFileSync, existsSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const API = 'http://localhost:8000/api';
// Dev-only "mailbox" written by backend/app/services/email_service.py
const OUTBOX = resolve(
	dirname(fileURLToPath(import.meta.url)),
	'../../backend/scratch/dev_outbox.json'
);

// Unique per run so the 60s per-user throttle and leftover rows never collide
const EMAIL = `pw-e2e-${Date.now()}@test.dev`;
const OLD_PASSWORD = 'OldPass123!';
const NEW_PASSWORD = 'NewPass456!';

const GENERIC_MESSAGE = 'If an account exists for this email, a reset link has been sent.';

function readOutbox(): { to: string; reset_link: string } | null {
	if (!existsSync(OUTBOX)) return null;
	return JSON.parse(readFileSync(OUTBOX, 'utf-8'));
}

function collectErrors(page: Page) {
	const errors: string[] = [];
	page.on('pageerror', (err) => errors.push(`pageerror: ${err.message}`));
	page.on('console', (msg) => {
		if (msg.type() === 'error') errors.push(`console.error: ${msg.text()}`);
	});
	return errors;
}

test.beforeAll(async ({ request }) => {
	// Backend must be running — fail fast with a clear message if not
	const health = await request.get('http://localhost:8000/').catch(() => null);
	if (!health || !health.ok()) {
		throw new Error('Backend is not running on http://localhost:8000 — start uvicorn first.');
	}
	const reg = await request.post(`${API}/auth/register`, {
		data: { email: EMAIL, password: OLD_PASSWORD, full_name: 'PW E2E' }
	});
	expect(reg.status()).toBe(201);
});

test.describe('Forgot/Reset password — happy path', () => {
	let resetLink = '';

	test('login page links to forgot-password', async ({ page }) => {
		const errors = collectErrors(page);
		await page.goto('/login');
		await page.getByRole('link', { name: 'Forgot password?' }).click();
		await expect(page).toHaveURL(/\/forgot-password/);
		expect(errors).toEqual([]);
	});

	test('forgot-password shows generic message and sends the link', async ({ page }) => {
		const errors = collectErrors(page);
		await page.goto('/forgot-password');
		await page.getByLabel('Email Address').fill(EMAIL);
		await page.getByRole('button', { name: 'Send Reset Link' }).click();

		await expect(page.getByText(GENERIC_MESSAGE)).toBeVisible();

		// The dev outbox should now hold a link addressed to our test user
		await expect.poll(() => readOutbox()?.to, { timeout: 5000 }).toBe(EMAIL);
		resetLink = readOutbox()!.reset_link;
		expect(resetLink).toContain('/reset-password?token=');
		expect(errors).toEqual([]);
	});

	test('reset page sets the new password and redirects to login', async ({ page }) => {
		const errors = collectErrors(page);
		await page.goto(resetLink);
		await page.getByLabel('New Password', { exact: true }).fill(NEW_PASSWORD);
		await page.getByLabel('Confirm Password').fill(NEW_PASSWORD);
		await page.getByRole('button', { name: 'Reset Password' }).click();

		await expect(page).toHaveURL(/\/login\?reset=success/);
		await expect(page.getByText('Password reset successful!')).toBeVisible();
		expect(errors).toEqual([]);
	});

	test('old password is rejected, new password logs in', async ({ page }) => {
		await page.goto('/login');
		await page.getByLabel('Email Address').fill(EMAIL);
		await page.getByLabel('Password', { exact: true }).fill(OLD_PASSWORD);
		await page.getByRole('button', { name: 'Sign In' }).click();
		await expect(page.getByText('Incorrect email or password')).toBeVisible();

		await page.getByLabel('Password', { exact: true }).fill(NEW_PASSWORD);
		await page.getByRole('button', { name: 'Sign In' }).click();
		await expect(page).toHaveURL(/\/dashboard/);
	});

	test('used token cannot be replayed', async ({ page }) => {
		await page.goto(resetLink);
		await page.getByLabel('New Password', { exact: true }).fill('Replay789!');
		await page.getByLabel('Confirm Password').fill('Replay789!');
		await page.getByRole('button', { name: 'Reset Password' }).click();
		await expect(page.getByText(/invalid or has expired/)).toBeVisible();
	});
});

test.describe('Forgot password — validation and edge cases', () => {
	test('empty email is blocked by the browser', async ({ page }) => {
		await page.goto('/forgot-password');
		await page.getByRole('button', { name: 'Send Reset Link' }).click();
		const invalid = await page
			.getByLabel('Email Address')
			.evaluate((el: HTMLInputElement) => !el.checkValidity());
		expect(invalid).toBe(true);
		// still on the form, no generic message
		await expect(page.getByText(GENERIC_MESSAGE)).not.toBeVisible();
	});

	test('malformed email is blocked by the browser', async ({ page }) => {
		await page.goto('/forgot-password');
		await page.getByLabel('Email Address').fill('not-an-email');
		await page.getByRole('button', { name: 'Send Reset Link' }).click();
		const invalid = await page
			.getByLabel('Email Address')
			.evaluate((el: HTMLInputElement) => !el.checkValidity());
		expect(invalid).toBe(true);
	});

	test('unknown email shows the identical generic message', async ({ page }) => {
		await page.goto('/forgot-password');
		await page.getByLabel('Email Address').fill('ghost-nobody@test.dev');
		await page.getByRole('button', { name: 'Send Reset Link' }).click();
		await expect(page.getByText(GENERIC_MESSAGE)).toBeVisible();
	});
});

test.describe('Reset password — validation and edge cases', () => {
	test('missing token disables the form with an error', async ({ page }) => {
		const errors = collectErrors(page);
		await page.goto('/reset-password');
		await expect(page.getByText(/reset link is invalid/)).toBeVisible();
		await expect(page.getByRole('button', { name: 'Reset Password' })).toBeDisabled();
		expect(errors).toEqual([]); // page must not crash without a token
	});

	test('password mismatch shows a client-side error', async ({ page }) => {
		await page.goto('/reset-password?token=bogus-token-value');
		await page.getByLabel('New Password', { exact: true }).fill('SomePass123');
		await page.getByLabel('Confirm Password').fill('OtherPass123');
		await page.getByRole('button', { name: 'Reset Password' }).click();
		await expect(page.getByText('Passwords do not match.')).toBeVisible();
	});

	test('short password is blocked before submit', async ({ page }) => {
		await page.goto('/reset-password?token=bogus-token-value');
		await page.getByLabel('New Password', { exact: true }).fill('short');
		await page.getByLabel('Confirm Password').fill('short');
		await page.getByRole('button', { name: 'Reset Password' }).click();
		const invalid = await page
			.getByLabel('New Password', { exact: true })
			.evaluate((el: HTMLInputElement) => !el.checkValidity());
		expect(invalid).toBe(true);
	});

	test('invalid token is rejected by the server with a safe message', async ({ page }) => {
		await page.goto('/reset-password?token=bogus-token-value');
		await page.getByLabel('New Password', { exact: true }).fill('ValidPass123');
		await page.getByLabel('Confirm Password').fill('ValidPass123');
		await page.getByRole('button', { name: 'Reset Password' }).click();
		await expect(page.getByText(/invalid or has expired/)).toBeVisible();
	});

	test('renders on a mobile viewport', async ({ page }) => {
		await page.setViewportSize({ width: 375, height: 667 });
		await page.goto('/reset-password?token=x');
		await expect(page.getByRole('button', { name: 'Reset Password' })).toBeVisible();
		await page.goto('/forgot-password');
		await expect(page.getByRole('button', { name: 'Send Reset Link' })).toBeVisible();
	});
});
