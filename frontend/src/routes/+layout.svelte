<script lang="ts">
	import favicon from '$lib/assets/favicon.svg';
	import '../app.css';
	import { page } from '$app/state';
	import { browser } from '$app/environment';
	import { goto } from '$app/navigation';
	import { Button } from '$lib/components/ui/button';
	import ThemeToggle from '$lib/components/theme-toggle.svelte';
	import { loadContents, clearCommonCache } from '$lib/stores/common';
	import { initTheme } from '$lib/stores/theme';
	import { getToken, getStoredUser, clearAuth, isAuthenticated as hasToken } from '$lib/auth';

	let { children } = $props();

	// Keep the theme store live (early init runs in app.html before paint; this
	// syncs runtime state + reacts to OS changes while in "system" mode).
	$effect(() => {
		initTheme();
	});

	// Pages reachable without a session — rendered bare, never auth-redirected
	const publicRoutes = ['/login', '/forgot-password', '/reset-password'];

	// Resolve auth synchronously at first render (SPA, ssr=false so localStorage is
	// available) so the protected shell is NEVER rendered for a logged-out user —
	// this is what prevents the dashboard "flash" before the login redirect.
	let isAuthenticated = $state(browser && hasToken());
	const isPublic = $derived(publicRoutes.includes(page.url.pathname));
	let user = $state<{ full_name?: string; email?: string } | null>(null);
	let streak = $state<number | null>(null);
	let revisionDue = $state(0);
	let roles = $state<string[] | null>(null);
	// Mobile slide-in sidebar (no effect on lg+ where the sidebar is always shown)
	let sidebarOpen = $state(false);

	// Sidebar items definition. `adminOnly` items are hidden from regular users
	// (the backend also enforces admin on those routes — this just avoids a
	// dead-end 403 in the UI).
	type MenuItem = { name: string; path: string; icon: string; adminOnly?: boolean };
	const menuItems: MenuItem[] = [
		{ name: 'Dashboard', path: '/dashboard', icon: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6' },
		{ name: 'Problems', path: '/problems', icon: 'M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253' },
		{ name: 'Topic Notes', path: '/topics', icon: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z' },
		{ name: 'Revision', path: '/revision', icon: 'M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z' },
		{ name: 'Roadmap', path: '/roadmap', icon: 'M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7' },
		{ name: 'LeetCode Import', path: '/leetcode-import', icon: 'M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4', adminOnly: true },
		{ name: 'Problem Import', path: '/admin/problem-import', icon: 'M19 14l-7 7m0 0l-7-7m7 7V3', adminOnly: true },
		{ name: 'Settings', path: '/settings', icon: 'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z' }
	];

	const isAdmin = $derived(roles?.includes('admin') ?? false);
	const visibleMenuItems = $derived(menuItems.filter((item) => !item.adminOnly || isAdmin));

	function logout() {
		clearAuth();
		clearCommonCache();
		isAuthenticated = false;
		user = null;
		goto('/login');
	}

	$effect(() => {
		// Track pathname to re-run authentication check when navigating
		const pathname = page.url.pathname;
		const token = getToken();

		if (token) {
			isAuthenticated = true;
			const storedUser = getStoredUser<{ full_name?: string; email?: string }>();
			if (storedUser) user = storedUser;
			// One bootstrap call (`/common/contents`, cached) replaces the separate
			// /auth/me + /dashboard/summary calls the shell used to make — it carries
			// roles (for admin nav) plus the streak / revision-due counts.
			if (roles === null) {
				loadContents()
					.then((c) => {
						roles = c.user.roles ?? [];
						streak = c.learning_summary.streak;
						revisionDue = c.learning_summary.revision_due_count ?? 0;
						if (!user) user = { full_name: c.user.name ?? undefined, email: c.user.email };
					})
					.catch(() => (roles = []));
			}
		} else {
			isAuthenticated = false;
			user = null;
			streak = null;
			revisionDue = 0;
			roles = null;
		}
	});

	$effect(() => {
		// Redirect logged-out users away from protected routes. The template never
		// renders protected content in this state, so there's no flash.
		if (!isPublic && !isAuthenticated) {
			goto('/login');
		}
	});

	// Close the mobile drawer whenever the route changes
	$effect(() => {
		page.url.pathname;
		sidebarOpen = false;
	});
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<title>AlgoLens AI — Visual DSA learning platform</title>
</svelte:head>

{#if isPublic}
	{@render children()}
{:else if isAuthenticated}
	<div class="flex min-h-screen app-bg text-slate-900">
		<!-- Mobile overlay: dims content and closes the drawer on tap (lg+: hidden) -->
		{#if sidebarOpen}
			<button
				type="button"
				aria-label="Close menu"
				class="fixed inset-0 z-40 bg-slate-900/50 backdrop-blur-[1px] lg:hidden"
				onclick={() => (sidebarOpen = false)}
			></button>
		{/if}

		<!-- Sidebar: off-canvas drawer on mobile, fixed rail on lg+.
		     Solid white in light; subtle glass in dark. -->
		<aside
			class="fixed inset-y-0 left-0 w-64 bg-card dark:bg-card/70 dark:backdrop-blur-xl border-r border-border flex flex-col p-6 z-50 transition-transform duration-300 ease-out lg:translate-x-0 {sidebarOpen ? 'translate-x-0 shadow-xl' : '-translate-x-full'} lg:shadow-none"
		>
			<div class="flex items-center gap-3 mb-10 pl-2">
				<div class="w-9 h-9 text-primary flex items-center justify-center bg-primary/10 rounded-lg">
					<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5" class="w-6 h-6">
						<circle cx="12" cy="12" r="6.75"/>
						<path stroke-linecap="round" d="M12 5.25 Q16.5 7.5 17.85 15.4"/>
						<path stroke-linecap="round" d="M17.85 8.6 Q18.75 15 12 18.75"/>
						<path stroke-linecap="round" d="M17.85 15.4 Q12 20 6.15 15.4"/>
						<path stroke-linecap="round" d="M12 18.75 Q5.25 16.5 6.15 8.6"/>
						<path stroke-linecap="round" d="M6.15 15.4 Q5.25 8.25 12 5.25"/>
						<path stroke-linecap="round" d="M6.15 8.6 Q12 4.1 17.85 8.6"/>
						<circle cx="12" cy="12" r="2.25" fill="currentColor" fill-opacity="0.25"/>
					</svg>
				</div>
				<span class="font-title font-bold text-lg flex items-center gap-1 text-foreground">
					AlgoLens <span class="bg-primary text-primary-foreground text-[10px] font-bold px-1.5 py-0.5 rounded tracking-wide">AI</span>
				</span>
			</div>

			<nav class="flex flex-col gap-1.5 flex-1">
				{#each visibleMenuItems as item}
					{@const isActive = page.url.pathname === item.path || page.url.pathname.startsWith(item.path + '/')}
					<a href={item.path} class="flex items-center gap-3 px-4 py-3 rounded-lg text-[14px] font-medium transition-all duration-200 {isActive ? 'text-primary bg-primary/10 font-semibold' : 'text-muted-foreground hover:text-primary hover:bg-muted'}">
						<svg class="w-5 h-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
							<path stroke-linecap="round" stroke-linejoin="round" d={item.icon} />
						</svg>
						<span class="flex-1">{item.name}</span>
						{#if item.name === 'Revision' && revisionDue > 0}
							<span class="ml-auto inline-flex min-w-5 items-center justify-center rounded-full bg-amber-100 px-1.5 py-0.5 text-[10px] font-bold text-amber-700" aria-label="{revisionDue} due">
								{revisionDue}
							</span>
						{/if}
					</a>
				{/each}
			</nav>

			<div class="border-t border-border pt-5 flex flex-col gap-4">
				<div class="flex items-center justify-between gap-2">
					<span class="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Theme</span>
					<ThemeToggle />
				</div>
				{#if user}
					<div class="flex items-center gap-3">
						<div class="w-9 h-9 bg-primary/10 text-primary rounded-full flex items-center justify-center font-bold border border-primary/20">
							{user.full_name ? user.full_name[0].toUpperCase() : 'U'}
						</div>
						<div class="flex flex-col overflow-hidden">
							<span class="text-[13px] font-semibold text-foreground truncate">{user.full_name || 'User'}</span>
							<span class="text-[11px] text-muted-foreground truncate">{user.email || 'user@algolens.ai'}</span>
						</div>
					</div>
				{/if}
				<Button variant="outline" class="w-full text-muted-foreground hover:text-destructive hover:bg-destructive/10 hover:border-destructive/40 text-xs py-2 h-9" onclick={logout}>
					<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" class="w-4 h-4 mr-2">
						<path stroke-linecap="round" stroke-linejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
					</svg>
					Logout
				</Button>
			</div>
		</aside>

		<!-- Main content area -->
		<div class="flex-1 lg:ml-64 flex flex-col min-h-screen">
			<header class="h-16 bg-card/90 dark:bg-card/65 backdrop-blur border-b border-border flex items-center justify-between px-4 sm:px-6 lg:px-8 sticky top-0 z-30">
				<div class="flex items-center gap-3 min-w-0">
					<button
						type="button"
						aria-label="Open menu"
						class="lg:hidden -ml-1 inline-flex h-9 w-9 items-center justify-center rounded-lg text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
						onclick={() => (sidebarOpen = true)}
					>
						<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" class="w-5 h-5">
							<path stroke-linecap="round" stroke-linejoin="round" d="M4 6h16M4 12h16M4 18h16" />
						</svg>
					</button>
					<h1 class="font-title text-base font-bold text-foreground truncate">
						{menuItems.find(item => page.url.pathname.startsWith(item.path))?.name || 'AlgoLens AI'}
					</h1>
				</div>
				<div>
					{#if streak !== null}
						<div class="flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-full border {streak > 0 ? 'bg-amber-50 text-amber-800 border-amber-200/50' : 'bg-slate-50 text-slate-500 border-slate-200'}">
							<span>🔥</span>
							<span>{streak > 0 ? `${streak} Day Streak` : 'Start your streak today'}</span>
						</div>
					{/if}
				</div>
			</header>

			<main class="p-4 sm:p-6 lg:p-8 flex-1">
				{#key page.url.pathname}
					<div class="animate-fade-in">
						{@render children()}
					</div>
				{/key}
			</main>
		</div>
	</div>
{:else}
	<!-- Logged-out on a protected route: neutral splash while redirecting to
	     /login. Never render protected content here (prevents the dashboard flash). -->
	<div class="flex items-center justify-center h-screen app-bg">
		<div class="animate-spin rounded-full h-10 w-10 border-4 border-muted border-t-primary"></div>
	</div>
{/if}
