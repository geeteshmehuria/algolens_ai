<script lang="ts">
	// Reusable illustrated page hero — a wide forest-green gradient panel with a
	// title/subtitle on the left, optional search/filter (controls) + action
	// buttons, and a lightweight inline-SVG illustration on the right that varies
	// by page. Theme-token driven (works light + dark); illustration is hidden on
	// small screens and animations respect prefers-reduced-motion (app.css guard).
	import type { Snippet } from "svelte";
	import { cn } from "$lib/utils";

	type Variant =
		| "notes"
		| "problems"
		| "dashboard"
		| "revision"
		| "roadmap"
		| "analytics"
		| "default";

	let {
		title,
		subtitle = "",
		eyebrow = "",
		variant = "default",
		showIllustration = true,
		compact = false,
		controls,
		actions,
		class: className = "",
	}: {
		title: string;
		subtitle?: string;
		eyebrow?: string;
		variant?: Variant;
		showIllustration?: boolean;
		compact?: boolean;
		controls?: Snippet;
		actions?: Snippet;
		class?: string;
	} = $props();
</script>

{#snippet sparkles()}
	<g class="text-primary" fill="currentColor">
		<path class="hero-sparkle" style="animation-delay:0s" d="M196 34 l2 5 5 2 -5 2 -2 5 -2 -5 -5 -2 5 -2 z" />
		<path class="hero-sparkle" style="animation-delay:0.9s" d="M30 30 l1.5 4 4 1.5 -4 1.5 -1.5 4 -1.5 -4 -4 -1.5 4 -1.5 z" />
		<circle class="hero-sparkle" style="animation-delay:1.6s" cx="206" cy="96" r="2.4" />
	</g>
{/snippet}

<section
	class={cn(
		"hero-surface animate-fade-in-up relative isolate overflow-hidden rounded-2xl",
		compact ? "p-5 sm:p-6" : "p-6 sm:p-8",
		className,
	)}
>
	<div class="relative z-10 flex flex-col gap-5 md:flex-row md:items-center md:justify-between md:gap-8">
		<div class="flex min-w-0 max-w-2xl flex-col gap-4">
			<div class="flex flex-col gap-1.5">
				{#if eyebrow}
					<span class="inline-flex w-fit items-center gap-1.5 rounded-full border border-primary/25 bg-primary/10 px-2.5 py-1 text-[11px] font-bold uppercase tracking-wide text-primary">
						{eyebrow}
					</span>
				{/if}
				<h1 class="font-title text-2xl font-extrabold tracking-tight text-foreground sm:text-3xl">
					{title}
				</h1>
				{#if subtitle}
					<p class="max-w-xl text-sm leading-relaxed text-muted-foreground">{subtitle}</p>
				{/if}
			</div>

			{#if controls}
				<div class="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center">
					{@render controls()}
				</div>
			{/if}

			{#if actions}
				<div class="flex flex-wrap items-center gap-2.5">
					{@render actions()}
				</div>
			{/if}
		</div>

		{#if showIllustration}
			<div class="pointer-events-none hidden shrink-0 select-none md:block" aria-hidden="true">
				<svg viewBox="0 0 220 160" class="h-32 w-52 lg:h-40 lg:w-64">
					<g class="animate-float">
						{#if variant === "notes"}
							<!-- Open book -->
							<path d="M110 124 C 84 110 56 110 30 118 L 30 58 C 56 50 84 50 110 64 Z" fill="hsl(var(--card))" stroke="hsl(var(--primary))" stroke-width="3" stroke-linejoin="round" />
							<path d="M110 124 C 136 110 164 110 190 118 L 190 58 C 164 50 136 50 110 64 Z" fill="hsl(var(--card))" stroke="hsl(var(--primary))" stroke-width="3" stroke-linejoin="round" />
							<g stroke="hsl(var(--primary) / 0.45)" stroke-width="2.5" stroke-linecap="round">
								<path d="M44 72 H 96" /><path d="M44 84 H 96" /><path d="M44 96 H 88" />
								<path d="M124 72 H 176" /><path d="M124 84 H 176" /><path d="M124 96 H 168" />
							</g>
							<!-- AI chip -->
							<g transform="translate(150 18)">
								<rect x="0" y="0" width="40" height="30" rx="7" fill="hsl(var(--primary) / 0.15)" stroke="hsl(var(--primary))" stroke-width="2.5" />
								<rect x="11" y="9" width="18" height="12" rx="3" fill="hsl(var(--primary))" />
								<g stroke="hsl(var(--primary))" stroke-width="2.5" stroke-linecap="round">
									<path d="M12 0 V -5" /><path d="M28 0 V -5" /><path d="M12 30 V 35" /><path d="M28 30 V 35" />
								</g>
							</g>
							<!-- Leaf -->
							<path d="M30 40 C 14 40 8 24 22 14 C 36 22 40 36 30 40 Z" fill="hsl(92 42% 48%)" />
						{:else if variant === "problems"}
							<!-- Code card -->
							<rect x="36" y="40" width="148" height="92" rx="12" fill="hsl(var(--card))" stroke="hsl(var(--primary))" stroke-width="3" />
							<rect x="36" y="40" width="148" height="22" rx="12" fill="hsl(var(--primary) / 0.12)" />
							<g fill="hsl(var(--primary))"><circle cx="50" cy="51" r="3" /><circle cx="62" cy="51" r="3" /><circle cx="74" cy="51" r="3" /></g>
							<g stroke="hsl(var(--primary))" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round" fill="none">
								<path d="M74 80 L 62 92 L 74 104" /><path d="M120 80 L 132 92 L 120 104" />
							</g>
							<g stroke="hsl(var(--primary) / 0.4)" stroke-width="3" stroke-linecap="round"><path d="M88 116 H 132" /></g>
							<!-- Check badge -->
							<g transform="translate(150 96)">
								<circle cx="20" cy="20" r="20" fill="hsl(142 60% 42%)" />
								<path d="M11 20 l6 6 12 -12" fill="none" stroke="#fff" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round" />
							</g>
						{:else if variant === "dashboard"}
							<!-- Growth bars + trend -->
							<g>
								<rect x="40" y="96" width="22" height="36" rx="5" fill="hsl(var(--primary) / 0.35)" />
								<rect x="72" y="78" width="22" height="54" rx="5" fill="hsl(var(--primary) / 0.55)" />
								<rect x="104" y="58" width="22" height="74" rx="5" fill="hsl(var(--primary))" />
								<rect x="136" y="40" width="22" height="92" rx="5" fill="hsl(142 60% 45%)" />
							</g>
							<path d="M48 92 L 84 74 L 116 56 L 150 36" fill="none" stroke="hsl(var(--primary))" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" />
							<circle cx="150" cy="36" r="5" fill="hsl(var(--card))" stroke="hsl(var(--primary))" stroke-width="3" />
							<path d="M180 44 C 168 44 162 30 174 22 C 186 30 188 42 180 44 Z" fill="hsl(92 42% 48%)" />
						{:else if variant === "revision"}
							<!-- Loop + clock -->
							<circle cx="110" cy="84" r="44" fill="hsl(var(--card))" stroke="hsl(var(--primary) / 0.5)" stroke-width="3" />
							<path d="M110 84 V 60" stroke="hsl(var(--primary))" stroke-width="4" stroke-linecap="round" />
							<path d="M110 84 L 130 96" stroke="hsl(var(--primary))" stroke-width="4" stroke-linecap="round" />
							<path d="M150 84 a40 40 0 1 1 -12 -28" fill="none" stroke="hsl(142 60% 45%)" stroke-width="4" stroke-linecap="round" />
							<path d="M138 44 l2 14 -15 -3 z" fill="hsl(142 60% 45%)" />
						{:else if variant === "roadmap"}
							<!-- Path nodes -->
							<path d="M40 120 C 80 120 80 70 120 70 C 160 70 160 40 192 40" fill="none" stroke="hsl(var(--primary) / 0.45)" stroke-width="3" stroke-dasharray="2 9" stroke-linecap="round" />
							<g>
								<circle cx="40" cy="120" r="11" fill="hsl(var(--primary))" />
								<circle cx="120" cy="70" r="11" fill="hsl(var(--card))" stroke="hsl(var(--primary))" stroke-width="3" />
								<circle cx="192" cy="40" r="11" fill="hsl(142 60% 45%)" />
							</g>
							<path d="M192 16 l2 6 6 2 -6 2 -2 6 -2 -6 -6 -2 6 -2 z" fill="hsl(43 92% 58%)" />
						{:else if variant === "analytics"}
							<!-- Donut ring + bars -->
							<circle cx="78" cy="84" r="38" fill="none" stroke="hsl(var(--primary) / 0.2)" stroke-width="12" />
							<circle cx="78" cy="84" r="38" fill="none" stroke="hsl(var(--primary))" stroke-width="12" stroke-linecap="round" stroke-dasharray="170 240" transform="rotate(-90 78 84)" />
							<g>
								<rect x="140" y="92" width="16" height="36" rx="4" fill="hsl(var(--primary) / 0.4)" />
								<rect x="164" y="72" width="16" height="56" rx="4" fill="hsl(var(--primary))" />
								<rect x="188" y="56" width="16" height="72" rx="4" fill="hsl(142 60% 45%)" />
							</g>
						{:else}
							<!-- default: leaves + spark -->
							<path d="M110 130 C 60 130 50 70 96 44 C 140 70 150 124 110 130 Z" fill="hsl(var(--primary) / 0.18)" stroke="hsl(var(--primary))" stroke-width="3" />
							<path d="M110 128 C 110 96 110 70 96 48" fill="none" stroke="hsl(var(--primary))" stroke-width="2.5" stroke-linecap="round" />
							<path d="M150 70 C 134 70 128 54 142 44 C 156 52 160 66 150 70 Z" fill="hsl(92 42% 48%)" />
						{/if}
					</g>
					{@render sparkles()}
				</svg>
			</div>
		{/if}
	</div>
</section>
