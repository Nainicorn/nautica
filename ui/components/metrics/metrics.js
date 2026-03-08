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
    visibleCount: 0,
    liveMode: false,
    $vesselValue: null,
    $avgConfValue: null,

    init() {
        this.element = document.querySelector('.__metrics');
        this._render(DEFAULTS);
        events.on('session:selected', (session) => this._load(session.id, session._live));
        events.on('viewer:frame-changed', (frameNum) => this._onFrameChanged(frameNum));
    },

    async _load(sessionId, live) {
        this.allDets = [];
        this.seenTracks = new Set();
        this.currentFrame = 0;
        this.totalVessels = 0;
        this.visibleCount = 0;
        this.liveMode = !!live;

        let dets = [];
        let anoms = [];

        try {
            const detData = await getDetections(sessionId);
            dets = detData.detections || [];
        } catch {}

        try {
            const anomData = await getAnomalies(sessionId);
            anoms = anomData.anomalies || [];
        } catch {}

        this.allDets = dets;
        const uniqueTracks = new Set(dets.filter(d => d.track_id).map(d => d.track_id));
        this.totalVessels = uniqueTracks.size;

        const tracks = uniqueTracks.size;
        const anomalyCount = anoms.length;

        let avgConfidence = '—';
        const confs = dets.filter(d => d.confidence != null).map(d => d.confidence);
        if (confs.length > 0) {
            const mean = confs.reduce((a, b) => a + b, 0) / confs.length;
            avgConfidence = (mean * 100).toFixed(1) + '%';
        }

        if (!this.liveMode) {
            // Static mode — show final values immediately
            this._render({ vessels: this.totalVessels, tracks, anomalyCount, avgConfidence });
            return;
        }

        // Live mode — start at 0 vessels, update as frames play
        this._render({ vessels: 0, tracks, anomalyCount, avgConfidence });
        this.$vesselValue = this.element.querySelector('.__metrics-card-value--accent');
        this.$avgConfValue = this.element.querySelector('.__metrics-card-value--conf');
    },

    _onFrameChanged(frameNum) {
        if (!this.liveMode || !this.allDets.length || !this.$vesselValue) return;
        if (frameNum < this.currentFrame) {
            this.seenTracks = new Set();
            this.visibleCount = 0;
        }
        this.currentFrame = frameNum;

        while (this.visibleCount < this.allDets.length) {
            const d = this.allDets[this.visibleCount];
            if (d.frame_number != null && d.frame_number > frameNum) break;
            const key = d.track_id || d.id;
            this.seenTracks.add(key);
            this.visibleCount++;
        }

        this.$vesselValue.textContent = this.seenTracks.size;

        if (this.$avgConfValue && this.visibleCount > 0) {
            const visible = this.allDets.slice(0, this.visibleCount);
            const confs = visible.filter(d => d.confidence != null).map(d => d.confidence);
            if (confs.length > 0) {
                const mean = confs.reduce((a, b) => a + b, 0) / confs.length;
                this.$avgConfValue.textContent = (mean * 100).toFixed(1) + '%';
            }
        }
    },

    _render(context) {
        this.element.innerHTML = template(context);
    }
};

export default metrics;
