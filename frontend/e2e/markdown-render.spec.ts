// Unit-style regression coverage for the shared Markdown renderer used by the
// Topic Notes page. Runs in the Playwright test runner (Node) — no browser or
// backend needed. Guards the fixes for raw-markdown / raw-table rendering and
// the escape-first XSS safety model.
import { test, expect } from '@playwright/test';
import { renderMarkdown } from '../src/lib/markdown';

test('renders ### headings as heading elements', () => {
	expect(renderMarkdown('### Key Definitions')).toMatch(/<h3[^>]*>Key Definitions<\/h3>/);
});

test('renders * and - bullets as a list with inline bold', () => {
	const html = renderMarkdown('* **Left/Start Pointer**: begins here\n- Right pointer');
	expect(html).toMatch(/<ul[^>]*>[\s\S]*<li[^>]*>[\s\S]*Left\/Start Pointer/);
	expect(html).toContain('<strong>Left/Start Pointer</strong>');
});

test('renders GFM pipe tables as real tables', () => {
	const html = renderMarkdown('| When | Use |\n| --- | --- |\n| sorted array | two pointers |');
	expect(html).toMatch(/<table[^>]*>/);
	expect(html).toMatch(/<th[^>]*>When<\/th>/);
	expect(html).toMatch(/<td[^>]*>two pointers<\/td>/);
});

test('renders fenced code blocks and inline italic', () => {
	expect(renderMarkdown('```python\nprint("hi")\n```')).toMatch(/<pre[^>]*>[\s\S]*<\/pre>/);
	expect(renderMarkdown('This is *emphasis* text')).toContain('<em>emphasis</em>');
});

test('escapes raw HTML (no XSS) — escape-first model', () => {
	const html = renderMarkdown('Hello <img src=x onerror=alert(1)> <script>alert(2)</script>');
	expect(html).not.toContain('<img');
	expect(html).not.toContain('<script>');
	expect(html).toContain('&lt;');
});

test('allows http links but neutralizes javascript: links', () => {
	const html = renderMarkdown('[ok](https://example.com) [bad](javascript:alert(1))');
	expect(html).toContain('href="https://example.com"');
	expect(html).not.toContain('javascript:');
	expect(html).toContain('href="#"');
});
