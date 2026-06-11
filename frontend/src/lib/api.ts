// Central API client — single place for the backend URL, auth header,
// and error extraction (FastAPI puts messages in `detail`).
export const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

export class ApiError extends Error {
	status: number;
	constructor(message: string, status: number) {
		super(message);
		this.status = status;
	}
}

export async function api<T = any>(path: string, options: RequestInit = {}): Promise<T> {
	const token = localStorage.getItem('token');
	const headers: Record<string, string> = {
		'Content-Type': 'application/json',
		...((options.headers as Record<string, string>) ?? {})
	};
	if (token) headers['Authorization'] = `Bearer ${token}`;

	const res = await fetch(`${API_BASE}/api${path}`, { ...options, headers });
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
}
