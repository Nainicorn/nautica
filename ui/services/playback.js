import { get } from './api.js';

export function getOverlayData(sessionId) {
    return get(`/sessions/${sessionId}/overlay`);
}

export function getFrameUrl(sessionId, frameNumber) {
    const padded = String(frameNumber).padStart(4, '0');
    return `/api/uploads/${sessionId}/frames/frame_${padded}.jpg`;
}
