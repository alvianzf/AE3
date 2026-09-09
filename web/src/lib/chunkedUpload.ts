// Chunked upload — client half of app/uploads.py. Splits a File into fixed-
// size pieces and uploads them sequentially, so a 200 MB file never sits in
// one HTTP request (nginx's client_max_body_size, currently well under
// 200 MB, only ever sees one chunk at a time) and a dropped connection only
// costs the current chunk, not the whole transfer — worth the extra
// round trips given a meaningful share of this app's real usage is a
// long-haul connection (server in Germany).
import { PUBLIC_API_BASE } from '$env/static/public';

// 4 MiB: comfortably under nginx's client_max_body_size (25m), and small
// enough that even a slow connection sending one chunk shouldn't trip
// nginx's default 60s client_body_timeout — see DEPLOY.md's nginx notes.
// A dropped chunk only costs 4 MiB of retry, not the whole file.
const CHUNK_BYTES = 4 * 1024 * 1024;
const MAX_RETRIES_PER_CHUNK = 3;

export interface ChunkedUploadProgress {
	sent: number;
	total: number;
}

async function apiCall(path: string, opts: RequestInit): Promise<any> {
	const res = await fetch(`${PUBLIC_API_BASE}/api${path}`, { credentials: 'include', ...opts });
	if (!res.ok) {
		const body = await res.json().catch(() => ({}));
		const d = body.detail;
		const message = (d && typeof d === 'object' ? d.message : d) || res.statusText;
		throw new Error(message);
	}
	return res.status === 204 ? null : res.json().catch(() => null);
}

async function uploadOneChunk(
	basePath: string,
	uploadId: string,
	blob: Blob
): Promise<void> {
	let lastErr: unknown;
	for (let attempt = 1; attempt <= MAX_RETRIES_PER_CHUNK; attempt++) {
		try {
			const fd = new FormData();
			fd.set('chunk', blob);
			await apiCall(`${basePath}/upload/${uploadId}/chunk`, { method: 'POST', body: fd });
			return;
		} catch (err) {
			lastErr = err;
		}
	}
	throw lastErr;
}

/**
 * Uploads `file` in CHUNK_BYTES pieces to `${basePath}/upload/{init,chunk,X}`
 * where X is `finishAction` (either `/sources` or `/me/files` — see
 * app/main.py). `completeBody` is merged into the POST body of the final
 * call (e.g. kind/origin/replaces for a source) — ignored when
 * `finishAction` is `'stage'`, which takes no body (app/main.py's
 * source_upload_stage). Returns whatever that final call returns.
 */
export async function chunkedUpload(
	basePath: string,
	file: File,
	completeBody: Record<string, unknown> = {},
	onProgress?: (p: ChunkedUploadProgress) => void,
	finishAction: 'complete' | 'stage' = 'complete'
): Promise<any> {
	const { upload_id } = await apiCall(`${basePath}/upload/init`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({
			filename: file.name,
			total_size: file.size,
			content_type: file.type || ''
		})
	});

	let sent = 0;
	for (let offset = 0; offset < file.size; offset += CHUNK_BYTES) {
		const blob = file.slice(offset, offset + CHUNK_BYTES);
		await uploadOneChunk(basePath, upload_id, blob);
		sent += blob.size;
		onProgress?.({ sent, total: file.size });
	}

	return apiCall(`${basePath}/upload/${upload_id}/${finishAction}`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: finishAction === 'stage' ? undefined : JSON.stringify(completeBody)
	});
}
