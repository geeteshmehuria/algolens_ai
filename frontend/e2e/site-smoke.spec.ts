import { test, expect, type Page } from '@playwright/test';
import { mkdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const API = 'http://localhost:8000/api';
const SHOTS = resolve(
	dirname(fileURLToPath(import.meta.url)),
	'../../testing-agent/reports/screenshots'
);

const EMAIL = `pw-e2e-smoke-${Date.now()}@test.dev`;
const PASSWORD = 'SmokeTest123!';
let token = '';
let problemId: number | null = null;
let topicId: number | null = null;

interface PageIssues {
	console: string[];
	pageErrors: string[];
	failedRequests: string[];
}

function watch(page: Page): PageIssues {
	const issues: PageIssues = { console: [], pageErrors: [], failedRequests: [] };
	page.on('console', (msg) => {
		if (msg.type() === 'error') issues.console.push(msg.text());
	});
	page.on('pageerror', (err) => issues.pageErrors.push(err.message));
	page.on('response', (res) => {
		if (res.status() >= 400) issues.failedRequests.push(`${res.status()} ${res.url()}`);
	});
	page.on('requestfailed', (req) => {
		issues.failedRequests.push(`FAILED ${req.url()} (${req.failure()?.errorText})`);
	});
	return issues;
}

async function noHorizontalOverflow(page: Page): Promise<string[]> {
	return page.evaluate(() => {
		const bad: string[] = [];
		if (document.documentElement.scrollWidth > document.documentElement.clientWidth + 1) {
			bad.push(
				`document scrollWidth ${document.documentElement.scrollWidth} > viewport ${document.documentElement.clientWidth}`
			);
		}
		return bad;
	});
}

async function authedGoto(page: Page, path: string) {
	await page.addInitScript((t) => localStorage.setItem('token', t), token);
	await page.goto(path);
	await page.waitForLoadState('networkidle');
}

test.beforeAll(async ({ request }) => {
	mkdirSync(SHOTS, { recursive: true });
	const health = await request.get('http://localhost:8000/').catch(() => null);
	if (!health || !health.ok()) throw new Error('Backend not running on :8000');

	const reg = await request.post(`${API}/auth/register`, {
		data: { email: EMAIL, password: PASSWORD, full_name: 'Smoke Tester' }
	});
	expect(reg.status()).toBe(201);
	const login = await request.post(`${API}/auth/login`, {
		data: { email: EMAIL, password: PASSWORD }
	});
	expect(login.status()).toBe(200);
	token = (await login.json()).access_token;

	// Discover real records for dynamic routes (public catalog endpoints)
	const problems = await (await request.get(`${API}/problems`)).json();
	if (Array.isArray(problems) && problems.length) problemId = problems[0].id;
	const topics = await (await request.get(`${API}/topics`)).json();
	if (Array.isArray(topics) && topics.length) topicId = topics[0].id;
});

const PUBLIC_PAGES = ['/login', '/forgot-password', '/reset-password'];
const AUTHED_PAGES = [
	'/dashboard',
	'/problems',
	'/topics',
	'/revision',
	'/roadmap',
	'/leetcode-import',
	'/settings'
];

for (const path of PUBLIC_PAGES) {
	test(`public ${path} loads clean`, async ({ page }) => {
		const issues = watch(page);
		await page.goto(path);
		await page.waitForLoadState('networkidle');
		await page.screenshot({ path: `${SHOTS}/public${path.replace(/\//g, '_')}.png`, fullPage: true });
		expect(issues.pageErrors, `page crashes on ${path}`).toEqual([]);
		expect(issues.console, `console errors on ${path}`).toEqual([]);
		expect(await noHorizontalOverflow(page)).toEqual([]);
	});
}

for (const path of AUTHED_PAGES) {
	test(`authed ${path} loads clean`, async ({ page }) => {
		const issues = watch(page);
		await authedGoto(page, path);
		await page.screenshot({ path: `${SHOTS}/authed${path.replace(/\//g, '_')}.png`, fullPage: true });
		expect(issues.pageErrors, `page crashes on ${path}`).toEqual([]);
		expect(issues.console, `console errors on ${path}`).toEqual([]);
		expect(issues.failedRequests, `failed API calls on ${path}`).toEqual([]);
		expect(await noHorizontalOverflow(page)).toEqual([]);
		// still on the page (not bounced to /login)
		expect(page.url()).toContain(path);
	});
}

test('problem detail page loads clean', async ({ page }) => {
	test.skip(problemId === null, 'no problems in DB');
	const issues = watch(page);
	await authedGoto(page, `/problems/${problemId}`);
	await page.screenshot({ path: `${SHOTS}/authed_problem_detail.png`, fullPage: true });
	expect(issues.pageErrors).toEqual([]);
	expect(issues.console).toEqual([]);
	expect(issues.failedRequests).toEqual([]);
});

test('topic notes page loads clean', async ({ page }) => {
	test.skip(topicId === null, 'no topics in DB');
	const issues = watch(page);
	await authedGoto(page, `/topics/${topicId}/notes`);
	await page.screenshot({ path: `${SHOTS}/authed_topic_notes.png`, fullPage: true });
	expect(issues.pageErrors).toEqual([]);
	expect(issues.console).toEqual([]);
});

test('root path redirects somewhere sensible', async ({ page }) => {
	await page.goto('/');
	await page.waitForLoadState('networkidle');
	await expect(page).toHaveURL(/\/(login|dashboard)/);
});

test('admin page as regular user does not crash', async ({ page }) => {
	const issues = watch(page);
	await authedGoto(page, '/admin/topic-notes');
	await page.screenshot({ path: `${SHOTS}/authed_admin_as_user.png`, fullPage: true });
	expect(issues.pageErrors, 'admin page crashes for non-admin').toEqual([]);
});

test('sidebar navigation works end to end', async ({ page }) => {
	await authedGoto(page, '/dashboard');
	for (const [label, path] of [
		['Problems', '/problems'],
		['Topic Notes', '/topics'],
		['Revision', '/revision'],
		['Roadmap', '/roadmap'],
		['Dashboard', '/dashboard']
	] as const) {
		await page.getByRole('link', { name: label, exact: false }).first().click();
		await expect(page).toHaveURL(new RegExp(path.replace('/', '\\/')));
	}
});

test('mobile viewport: key pages have no horizontal overflow', async ({ page }) => {
	await page.setViewportSize({ width: 375, height: 667 });
	for (const path of ['/login', '/forgot-password']) {
		await page.goto(path);
		await page.waitForLoadState('networkidle');
		const overflow = await noHorizontalOverflow(page);
		await page.screenshot({ path: `${SHOTS}/mobile${path.replace(/\//g, '_')}.png` });
		expect(overflow, `horizontal overflow on mobile ${path}`).toEqual([]);
	}
});

test('tablet viewport: dashboard renders', async ({ page }) => {
	await page.setViewportSize({ width: 768, height: 1024 });
	const issues = watch(page);
	await authedGoto(page, '/dashboard');
	await page.screenshot({ path: `${SHOTS}/tablet_dashboard.png`, fullPage: true });
	expect(issues.pageErrors).toEqual([]);
});
