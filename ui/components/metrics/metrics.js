import template from './metrics.hbs';
import './metrics.css';
import { getDetections, getAnomalies } from '../../services/analysis.js';
import events from '../../services/events.js';

const DEFAULTS = { vessels: '—', tracks: '—', anomalyCount: '—', avgConfidence: '—' };

const metrics = {
    element: null,
    allDets: [],
    seenTracks: new Set(),
    currentFrame: 0,
    totalVessels: 0,
    $vesselValue: null,

    init() {
        this.element = document.querySelector('.__metrics');
        this._render(DEFAULTS);
        events.on('session:selected', (session) => this._load(session.id));
        events.on('viewer:frame-changed', (frameNum) => this._onFrameChanged(frameNum));
    },

    async _load(sessionId) {
        this._render({ vessels: '...', tracks: '...', anomalyCount: '...', avgConfidence: '...' });
        this.allDets = [];
        this.seenTracks = new Set();
        this.currentFrame = 0;
        this.totalVessels = 0;

        try {
            const [detData, anomData] = await Promise.all([
                getDetections(sessionId),
                getAnomalies(sessionId),
            ]);

            const dets = detData.detections;
            const anoms = anomData.anomalies;

            this.allDets = dets;
            this.totalVessels = new Set(dets.map(d => d.track_id || d.id)).size;

            const tracks = dets.filter(d => d.status === 'tracking').length;
            const anomalyCount = anoms.length;

            let avgConfidence = '—';
            const confs = dets.filter(d => d.confidence != null).map(d => d.confidence);
            if (confs.length > 0) {
                const mean = confs.reduce((a, b) => a + b, 0) / confs.length;
                avgConfidence = (mean * 100).toFixed(1) + '%';
            }

            this._render({ vessels: 0, tracks, anomalyCount, avgConfidence });
            this.$vesselValue = this.element.querySelector('.__metrics-card-value--accent');
        } catch (err) {
            this._render(DEFAULTS);
        }
    },

    _onFrameChanged(frameNum) {
        if (!this.allDets.length || !this.$vesselValue) return;
        if (frameNum < this.currentFrame) {
            this.seenTracks = new Set();
        }
        this.currentFrame = frameNum;

        for (const d of this.allDets) {
            if (d.frame_number != null && d.frame_number > frameNum) break;
            const key = d.track_id || d.id;
            this.seenTracks.add(key);
        }

        this.$vesselValue.textContent = this.seenTracks.size;
    },

    _render(context) {
        this.element.innerHTML = template(context);
    }
};

export default metrics;
