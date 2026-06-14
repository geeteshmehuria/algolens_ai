// Client cache for the common bootstrap (`/common/contents`) and lookup
// (`/common/master-data`) APIs. Caches across in-app navigations so pages stop
// re-fetching the same user/lookup data on every visit. Cleared on logout.

import { api } from '$lib/api';

export interface CommonContents {
	user: {
		id: number;
		name: string | null;
		email: string;
		roles: string[];
		permissions: string[];
	};
	preferences: Record<string, unknown>;
	feature_flags: Record<string, boolean>;
	app_config: Record<string, unknown>;
	learning_summary: {
		solved_count: number;
		attempted_count: number;
		streak: number;
		revision_due_count: number;
	};
	version: string;
}

export interface MasterData {
	topics?: Array<{ id: number; name: string }> | null;
	patterns?: Array<{ id: number; name: string; topic_id: number }> | null;
	difficulties?: string[] | null;
	languages?: string[] | null;
}

let _contents: CommonContents | null = null;
let _contentsPromise: Promise<CommonContents> | null = null;

/** Fetch the bootstrap contents once and cache it. Concurrent callers share the
 *  same in-flight request; later callers get the cached value. */
export async function loadContents(force = false): Promise<CommonContents> {
	if (force) clearContents();
	if (_contents) return _contents;
	if (!_contentsPromise) {
		_contentsPromise = api<CommonContents>('/common/contents')
			.then((c) => {
				_contents = c;
				return c;
			})
			.catch((e) => {
				_contentsPromise = null; // allow retry on failure
				throw e;
			});
	}
	return _contentsPromise;
}

export function getCachedContents(): CommonContents | null {
	return _contents;
}

export function clearContents(): void {
	_contents = null;
	_contentsPromise = null;
}

// --- master data (cached per key) ---
const _master: MasterData = {};
const _masterPromises: Record<string, Promise<MasterData>> = {};

/** Load the requested lookup keys, fetching only the ones not already cached. */
export async function loadMasterData(keys: Array<keyof MasterData>): Promise<MasterData> {
	const missing = keys.filter((k) => _master[k] === undefined);
	if (missing.length) {
		const cacheKey = [...missing].sort().join(',');
		if (!_masterPromises[cacheKey]) {
			_masterPromises[cacheKey] = api<MasterData>(`/common/master-data?keys=${missing.join(',')}`)
				.then((data) => {
					for (const k of missing) (_master as Record<string, unknown>)[k] = data[k] ?? null;
					return data;
				})
				.finally(() => {
					delete _masterPromises[cacheKey];
				});
		}
		await _masterPromises[cacheKey];
	}
	const out: MasterData = {};
	for (const k of keys) (out as Record<string, unknown>)[k] = _master[k];
	return out;
}

export function clearMasterData(): void {
	for (const k of Object.keys(_master)) delete (_master as Record<string, unknown>)[k];
}

/** Drop all cached common data (call on logout). */
export function clearCommonCache(): void {
	clearContents();
	clearMasterData();
}
