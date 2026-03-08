import { get } from './api.js';

const API_BASE = import.meta.env.VITE_API_BASE || '/api';

export function getDetections(sessionId) {
    return get(`/sessions/${sessionId}/detections`);
}

export function getAnomalies(sessionId) {
    return get(`/sessions/${sessionId}/anomalies`);
}

export function getReport(sessionId) {
    return get(`/sessions/${sessionId}/report`);
}

export function getReportStreamUrl(sessionId) {
    return `${API_BASE}/sessions/${sessionId}/report/stream`;
}
