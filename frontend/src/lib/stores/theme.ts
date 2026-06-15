// Theme store: light / dark / system, persisted in localStorage and applied as
// a `.dark` class on <html>. The early init script in app.html applies the saved
// theme before first paint (no flash); this store keeps it in sync at runtime
// and reacts to OS changes while in "system" mode.
import { writable } from "svelte/store";
import { browser } from "$app/environment";

export type Theme = "light" | "dark" | "system";

const STORAGE_KEY = "theme";

function getStored(): Theme {
	if (!browser) return "system";
	const t = localStorage.getItem(STORAGE_KEY);
	return t === "light" || t === "dark" || t === "system" ? t : "system";
}

function systemPrefersDark(): boolean {
	return browser && window.matchMedia("(prefers-color-scheme: dark)").matches;
}

/** Whether the given preference resolves to a dark appearance right now. */
export function resolveDark(t: Theme): boolean {
	return t === "dark" || (t === "system" && systemPrefersDark());
}

function apply(t: Theme): void {
	if (!browser) return;
	const dark = resolveDark(t);
	const el = document.documentElement;
	el.classList.toggle("dark", dark);
	el.style.colorScheme = dark ? "dark" : "light";
}

/** Current preference. `resolved` reflects whether dark is actually active. */
export const theme = writable<Theme>(getStored());

let current: Theme = getStored();
theme.subscribe((v) => (current = v));

export function setTheme(t: Theme): void {
	if (browser) localStorage.setItem(STORAGE_KEY, t);
	theme.set(t);
	apply(t);
}

let initialized = false;
/** Call once on app start (client). Idempotent. */
export function initTheme(): void {
	if (!browser || initialized) return;
	initialized = true;
	apply(current);
	// Keep "system" mode live as the OS preference changes.
	window
		.matchMedia("(prefers-color-scheme: dark)")
		.addEventListener("change", () => {
			if (current === "system") apply("system");
		});
}
