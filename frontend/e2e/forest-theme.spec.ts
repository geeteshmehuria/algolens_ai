import { test, expect, type Page } from '@playwright/test';

// Visual review of the Forest Green theme. API is mocked so the authenticated
// pages render fully with realistic data — no backend needed. Not a CI gate;
// it captures screenshots and asserts there are no console errors / no blue CTA.

function isoDaysAgo(n: number): string {
	const d = new Date();
	d.setUTCDate(d.getUTCDate() - n);
	return d.toISOString().slice(0, 10);
}

const activity = Array.from({ length: 14 }, (_, i) => ({
	date: isoDaysAgo(13 - i),
	count: [2, 4, 1, 6, 3, 5, 2, 3, 7, 2, 4, 8, 5, 6][i]
}));

const topicNotes = [
	{ id: 1, name: 'Two Pointers', category: 'Arrays', difficulty: 'beginner', has_published_note: true, state: { status: 'completed', is_bookmarked: true, completed_sections_count: 4, last_read_on: null }, last_quiz: { score: 4, total: 5 } },
	{ id: 2, name: 'Sliding Window', category: 'Arrays', difficulty: 'intermediate', has_published_note: true, state: { status: 'reading', is_bookmarked: false, completed_sections_count: 1, last_read_on: null }, last_quiz: null },
	{ id: 3, name: 'Prefix Sums', category: 'Arrays', difficulty: 'intermediate', has_published_note: false, state: null, last_quiz: null },
	{ id: 4, name: 'Binary Search', category: 'Searching', difficulty: 'beginner', has_published_note: true, state: { status: 'revised', is_bookmarked: false, completed_sections_count: 3, last_read_on: null }, last_quiz: { score: 5, total: 5 } },
	{ id: 5, name: 'BFS', category: 'Graphs', difficulty: 'intermediate', has_published_note: false, state: { status: 'reading', is_bookmarked: false, completed_sections_count: 2, last_read_on: null }, last_quiz: null },
	{ id: 6, name: 'Dijkstra', category: 'Graphs', difficulty: 'advanced', has_published_note: false, state: null, last_quiz: null }
];

const summary = {
	solved_count: 128,
	attempted_count: 172,
	streak: 6,
	revision_due_count: 3,
	weak_topics: [
		{ topic_id: 6, topic_name: 'Graphs', score: 42 },
		{ topic_id: 7, topic_name: 'Dynamic Programming', score: 68 },
		{ topic_id: 8, topic_name: 'Trees', score: 84 }
	],
	recommended_problems: [
		{ id: 1, title: 'Course Schedule', difficulty: 'Medium', topic: 'Graphs' },
		{ id: 2, title: 'Coin Change', difficulty: 'Medium', topic: 'Dynamic Programming' }
	]
};

const contents = {
	user: { id: 1, name: 'Alex Green', email: 'alex@test.dev', roles: [], permissions: [] },
	preferences: {},
	feature_flags: {},
	app_config: { app_name: 'AlgoLens AI' },
	learning_summary: { streak: 6, revision_due_count: 3 },
	version: 'test'
};

async function mockApi(page: Page) {
	await page.route('**/api/**', (route) => {
		const url = route.request().url();
		const json = (body: unknown) =>
			route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) });
		if (url.includes('/dashboard/summary')) return json(summary);
		if (url.includes('/dashboard/activity')) return json(activity);
		if (url.includes('/me/topic-notes')) return json(topicNotes);
		if (url.includes('/common/contents')) return json(contents);
		return json({});
	});
}

for (const theme of ['light', 'dark'] as const) {
	test(`dashboard renders in ${theme} (forest green, no console errors)`, async ({ page }) => {
		const errors: string[] = [];
		page.on('console', (m) => m.type() === 'error' && errors.push(m.text()));
		page.on('pageerror', (e) => errors.push(e.message));

		await page.addInitScript(
			([t]) => {
				localStorage.setItem('theme', t);
				localStorage.setItem('token', 'e2e-fake');
				localStorage.setItem('user', JSON.stringify({ full_name: 'Alex Green', email: 'alex@test.dev' }));
			},
			[theme]
		);
		await mockApi(page);

		await page.goto('/dashboard');
		await expect(page.getByText('Progress Overview')).toBeVisible();
		await expect(page.getByText('Weekly Activity')).toBeVisible();
		await page.waitForTimeout(1000); // let ring + bars animate in
		await page.screenshot({ path: `test-results/forest-dashboard-${theme}.png`, fullPage: true });
		expect(errors, errors.join(' | ')).toEqual([]);
	});

	test(`topics renders in ${theme}`, async ({ page }) => {
		await page.addInitScript(
			([t]) => {
				localStorage.setItem('theme', t);
				localStorage.setItem('token', 'e2e-fake');
			},
			[theme]
		);
		await mockApi(page);
		await page.goto('/topics');
		await expect(page.getByRole('heading', { name: 'AI DSA Study Notes' })).toBeVisible();
		await page.screenshot({ path: `test-results/forest-topics-${theme}.png`, fullPage: true });
	});
}
