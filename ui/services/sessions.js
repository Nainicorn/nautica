import { get, post, del } from './api.js';

export function getSessions() {
    return get('/sessions');
}

export function getSession(id) {
    return get(`/sessions/${id}`);
}

export function createSession(name, fileType) {
    return post('/sessions', { name, file_type: fileType || null });
}

export function processSession(sessionId) {
    return post(`/sessions/${sessionId}/process`);
}

export function deleteSession(sessionId) {
    return del(`/sessions/${sessionId}`);
}
