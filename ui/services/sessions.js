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

export function detectSession(sessionId) {
    return post(`/sessions/${sessionId}/detect`);
}

export function trackSession(sessionId) {
    return post(`/sessions/${sessionId}/track`);
}

export function analyzeSession(sessionId) {
    return post(`/sessions/${sessionId}/analyze`);
}

export function deleteSession(sessionId) {
    return del(`/sessions/${sessionId}`);
}
