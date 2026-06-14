// Single source of truth for client auth-token storage.
//
// Why centralize: previously every page read `localStorage.getItem('token')`
// directly. Funnelling it through one module shrinks the token's exposure
// surface and means a future migration to HttpOnly cookies touches ONLY this
// file (and api.ts's credentials mode) instead of a dozen components.
//
// Security reality (by design, documented): with a SPA + JWT bearer flow the
// login response body and the Authorization header are visible in the browser
// Network tab — that cannot be hidden while JavaScript needs the token to call
// the API. The only way to keep a token out of JS is HttpOnly cookies, which is
// a larger, separate migration (CORS credentials + CSRF). What we DO guarantee
// here: the token is never logged, and all auth state is cleared on logout.

const TOKEN_KEY = 'token';
const USER_KEY = 'user';

function hasStorage(): boolean {
	return typeof localStorage !== 'undefined';
}

export function getToken(): string | null {
	return hasStorage() ? localStorage.getItem(TOKEN_KEY) : null;
}

export function setToken(token: string): void {
	if (hasStorage()) localStorage.setItem(TOKEN_KEY, token);
}

export function isAuthenticated(): boolean {
	return !!getToken();
}

export function setStoredUser(user: unknown): void {
	if (hasStorage()) localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function getStoredUser<T = unknown>(): T | null {
	if (!hasStorage()) return null;
	const raw = localStorage.getItem(USER_KEY);
	if (!raw) return null;
	try {
		return JSON.parse(raw) as T;
	} catch {
		localStorage.removeItem(USER_KEY);
		return null;
	}
}

/** Wipe all client auth state. Call on logout / 401. */
export function clearAuth(): void {
	if (!hasStorage()) return;
	localStorage.removeItem(TOKEN_KEY);
	localStorage.removeItem(USER_KEY);
}
