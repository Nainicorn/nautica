const API_BASE = import.meta.env.VITE_API_BASE || '/api';

async function request(path, options = {}) {
    const res = await fetch(`${API_BASE}${path}`, {
        headers: { 'Content-Type': 'application/json' },
        ...options,
    });

    if (!res.ok) {
        const error = new Error(`API ${res.status}: ${res.statusText}`);
        error.status = res.status;
        throw error;
    }

    return res.json();
}

export function get(path) {
    return request(path);
}

export function post(path, body) {
    return request(path, {
        method: 'POST',
        body: JSON.stringify(body),
    });
}

export function del(path) {
    return request(path, { method: 'DELETE' });
}

export function uploadFile(sessionId, file, onProgress) {
    return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        const formData = new FormData();
        formData.append('session_id', sessionId);
        formData.append('file', file);

        xhr.upload.addEventListener('progress', (e) => {
            if (e.lengthComputable && onProgress) {
                onProgress(Math.round((e.loaded / e.total) * 100));
            }
        });

        xhr.addEventListener('load', () => {
            if (xhr.status >= 200 && xhr.status < 300) {
                resolve(JSON.parse(xhr.responseText));
            } else {
                const error = new Error(`Upload failed: ${xhr.status}`);
                error.status = xhr.status;
                reject(error);
            }
        });

        xhr.addEventListener('error', () => reject(new Error('Upload network error')));
        xhr.addEventListener('abort', () => reject(new Error('Upload aborted')));

        xhr.open('POST', `${API_BASE}/upload`);
        xhr.send(formData);
    });
}
