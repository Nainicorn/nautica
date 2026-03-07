import { get } from './api.js';

export function getDetections(sessionId) {
    return get(`/sessions/${sessionId}/detections`);
}

export function getAnomalies(sessionId) {
    return get(`/sessions/${sessionId}/anomalies`);
}

export function getReport(sessionId) {
    return get(`/sessions/${sessionId}/report`);
}
