// Central API client — single place for the backend URL, auth header,
import { getToken } from '$lib/auth';

const rawApiUrl = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';
export const API_BASE = rawApiUrl.replace(/\/+$/, '');

export class ApiError extends Error {
	status: number;
	constructor(message: string, status: number) {
		super(message);
		this.status = status;
	}
}

const inflightRequests = new Map<string, Promise<any>>();

export async function api<T = any>(path: string, options: RequestInit = {}): Promise<T> {
	const method = (options.method ?? 'GET').toUpperCase();
	const isGet = method === 'GET';
	const key = isGet ? path : null;

	if (key && inflightRequests.has(key)) {
		return inflightRequests.get(key) as Promise<T>;
	}

	const promise = (async () => {
		const token = getToken();
		const headers: Record<string, string> = {
			'Content-Type': 'application/json',
			...((options.headers as Record<string, string>) ?? {})
		};
		if (token) headers['Authorization'] = `Bearer ${token}`;

		const cleanPath = path.startsWith('/') ? path : `/${path}`;
		const res = await fetch(`${API_BASE}/api${cleanPath}`, { ...options, headers });
		if (!res.ok) {
			let detail = `Request failed (${res.status})`;
			try {
				const body = await res.json();
				if (body?.detail) detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail);
			} catch {
				// non-JSON error body — keep generic message
			}
			throw new ApiError(detail, res.status);
		}
		return res.json();
	})();

	if (key) {
		inflightRequests.set(key, promise);
		promise.finally(() => {
			inflightRequests.delete(key);
		});
	}

	return promise;
}
