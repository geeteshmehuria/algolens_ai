// Shared, XSS-safe Markdown -> HTML renderer for AI-generated note content.
//
// Safety model: the raw source is HTML-escaped FIRST (`&`, `<`, `>`, `"`), then
// only a fixed set of our own safe tags/classes is injected. Because every
// angle bracket in the source is neutralised before any markup is added, the
// output can be used with Svelte's {@html ...} without risking script/attribute
// injection — no external sanitizer needed. Links are additionally restricted
// to http/https/mailto and get rel="noopener noreferrer nofollow".
//
// Supported: headings (#..######), unordered lists (-, *, +), ordered lists,
// **bold**, *italic*/_italic_, `inline code`, fenced ``` code blocks ```,
// GFM pipe tables, blockquotes, and paragraphs.

function escapeHtml(src: string): string {
	return src
		.replace(/&/g, '&amp;')
		.replace(/</g, '&lt;')
		.replace(/>/g, '&gt;')
		.replace(/"/g, '&quot;');
}

// Inline formatting. Input is ALREADY HTML-escaped.
function renderInline(escaped: string): string {
	let t = escaped;

	// Inline code — render first so its contents are not further formatted.
	t = t.replace(
		/`([^`]+)`/g,
		'<code class="bg-slate-100 text-slate-700 px-1.5 py-0.5 rounded font-mono text-[13px] font-semibold border border-slate-200/60">$1</code>'
	);

	// Links [label](url) — restrict the scheme; encode quotes in href.
	t = t.replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, (_m, label: string, url: string) => {
		const safeHref = /^(https?:|mailto:)/i.test(url) ? url.replace(/"/g, '%22') : '#';
		return `<a href="${safeHref}" target="_blank" rel="noopener noreferrer nofollow" class="text-blue-600 underline hover:text-blue-700">${label}</a>`;
	});

	// Bold then italic. Bold uses ** / __; italic uses single * / _.
	t = t.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
	t = t.replace(/__([^_]+)__/g, '<strong>$1</strong>');
	t = t.replace(/(^|[^*])\*([^*\s][^*]*?)\*(?!\*)/g, '$1<em>$2</em>');
	t = t.replace(/(^|[^_])_([^_\s][^_]*?)_(?!_)/g, '$1<em>$2</em>');

	return t;
}

function splitRow(line: string): string[] {
	let s = line.trim();
	if (s.startsWith('|')) s = s.slice(1);
	if (s.endsWith('|')) s = s.slice(0, -1);
	return s.split('|').map((c) => c.trim());
}

function isTableSeparator(line: string): boolean {
	// e.g. | --- | :--: | ---: |
	return /^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$/.test(line);
}

/** Render Markdown to a safe HTML string. */
export function renderMarkdown(md: string): string {
	if (!md) return '';

	const escaped = escapeHtml(md);
	const lines = escaped.split('\n');
	const out: string[] = [];
	let i = 0;

	const flushParagraph = (buf: string[]) => {
		if (buf.length === 0) return;
		const html = buf.map((l) => renderInline(l.trim())).join('<br>');
		out.push(`<p class="text-slate-600 leading-relaxed text-sm my-3">${html}</p>`);
		buf.length = 0;
	};

	while (i < lines.length) {
		const line = lines[i];

		// Blank line
		if (line.trim() === '') {
			i++;
			continue;
		}

		// Fenced code block ```lang ... ```
		const fence = line.match(/^\s*```([a-zA-Z0-9]*)\s*$/);
		if (fence) {
			const code: string[] = [];
			i++;
			while (i < lines.length && !/^\s*```\s*$/.test(lines[i])) {
				code.push(lines[i]);
				i++;
			}
			i++; // consume closing fence
			out.push(
				`<pre class="bg-slate-900 text-slate-100 p-4 rounded-xl font-mono text-[12px] my-3 overflow-x-auto whitespace-pre">${code.join('\n')}</pre>`
			);
			continue;
		}

		// GFM table: a row line followed by a separator row
		if (line.includes('|') && i + 1 < lines.length && isTableSeparator(lines[i + 1])) {
			const header = splitRow(line);
			i += 2; // skip header + separator
			const body: string[][] = [];
			while (i < lines.length && lines[i].includes('|') && lines[i].trim() !== '') {
				body.push(splitRow(lines[i]));
				i++;
			}
			const thead =
				'<thead><tr>' +
				header
					.map(
						(c) =>
							`<th class="border border-slate-200 bg-slate-50 px-3 py-2 text-left text-xs font-bold text-slate-700">${renderInline(c)}</th>`
					)
					.join('') +
				'</tr></thead>';
			const tbody =
				'<tbody>' +
				body
					.map(
						(row) =>
							'<tr>' +
							row
								.map(
									(c) =>
										`<td class="border border-slate-200 px-3 py-2 text-[13px] text-slate-600 align-top">${renderInline(c)}</td>`
								)
								.join('') +
							'</tr>'
					)
					.join('') +
				'</tbody>';
			out.push(
				`<div class="my-3 overflow-x-auto"><table class="w-full border-collapse text-xs">${thead}${tbody}</table></div>`
			);
			continue;
		}

		// Heading
		const heading = line.match(/^\s*(#{1,6})\s+(.*)$/);
		if (heading) {
			const level = heading[1].length;
			const sizes: Record<number, string> = {
				1: 'font-title text-lg font-extrabold text-slate-900 mt-5 mb-2.5',
				2: 'font-title text-base font-bold text-slate-900 mt-5 mb-2',
				3: 'text-xs font-bold text-slate-800 uppercase tracking-wider mt-4 mb-1.5',
				4: 'text-sm font-bold text-slate-700 mt-3 mb-1.5',
				5: 'text-[13px] font-bold text-slate-700 mt-2 mb-1',
				6: 'text-xs font-semibold text-slate-600 mt-2 mb-1'
			};
			out.push(`<h${level} class="${sizes[level]}">${renderInline(heading[2].trim())}</h${level}>`);
			i++;
			continue;
		}

		// Blockquote
		if (/^\s*&gt;\s?/.test(line)) {
			const quote: string[] = [];
			while (i < lines.length && /^\s*&gt;\s?/.test(lines[i])) {
				quote.push(lines[i].replace(/^\s*&gt;\s?/, ''));
				i++;
			}
			out.push(
				`<blockquote class="border-l-4 border-blue-200 bg-blue-50/30 rounded-r-lg py-2 pr-3 pl-4 my-3 text-slate-600 italic text-sm">${quote
					.map((l) => renderInline(l.trim()))
					.join('<br>')}</blockquote>`
			);
			continue;
		}

		// Unordered list (-, *, +)
		if (/^\s*[-*+]\s+/.test(line)) {
			const items: string[] = [];
			while (i < lines.length && /^\s*[-*+]\s+/.test(lines[i])) {
				items.push(lines[i].replace(/^\s*[-*+]\s+/, ''));
				i++;
			}
			out.push(
				`<ul class="list-disc pl-5 my-3 flex flex-col gap-1.5 text-sm text-slate-600 marker:text-slate-400">${items
					.map((it) => `<li class="leading-relaxed">${renderInline(it.trim())}</li>`)
					.join('')}</ul>`
			);
			continue;
		}

		// Ordered list (1. 2. ...)
		if (/^\s*\d+\.\s+/.test(line)) {
			const items: string[] = [];
			while (i < lines.length && /^\s*\d+\.\s+/.test(lines[i])) {
				items.push(lines[i].replace(/^\s*\d+\.\s+/, ''));
				i++;
			}
			out.push(
				`<ol class="list-decimal pl-5 my-3 flex flex-col gap-1.5 text-sm text-slate-600 marker:text-slate-400 marker:font-semibold">${items
					.map((it) => `<li class="leading-relaxed">${renderInline(it.trim())}</li>`)
					.join('')}</ol>`
			);
			continue;
		}

		// Paragraph: gather contiguous "plain" lines
		const para: string[] = [];
		while (
			i < lines.length &&
			lines[i].trim() !== '' &&
			!/^\s*```/.test(lines[i]) &&
			!/^\s*#{1,6}\s+/.test(lines[i]) &&
			!/^\s*[-*+]\s+/.test(lines[i]) &&
			!/^\s*\d+\.\s+/.test(lines[i]) &&
			!/^\s*&gt;\s?/.test(lines[i]) &&
			!(lines[i].includes('|') && i + 1 < lines.length && isTableSeparator(lines[i + 1]))
		) {
			para.push(lines[i]);
			i++;
		}
		flushParagraph(para);
	}

	return out.join('\n');
}
