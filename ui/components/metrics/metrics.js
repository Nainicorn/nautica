import template from './metrics.hbs';
import './metrics.css';
import { getDetections, getAnomalies } from '../../services/analysis.js';
import events from '../../services/events.js';

const DEFAULTS = { vessels: '—', tracks: '—', anomalyCount: '—', avgConfidence: '—' };

const metrics = {
    element: null,

    init() {
        this.element = document.querySelector('.__metrics');
        this._render(DEFAULTS);
        events.on('session:selected', (session) => this._load(session.id));
    },

    async _load(sessionId) {
        this._render({ vessels: '...', tracks: '...', anomalyCount: '...', avgConfidence: '...' });
        try {
            const [detData, anomData] = await Promise.all([
                getDetections(sessionId),
                getAnomalies(sessionId),
            ]);

            const dets = detData.detections;
            const anoms = anomData.anomalies;

            const vessels = dets.length;
            const tracks = dets.filter(d => d.status === 'tracking').length;
            const anomalyCount = anoms.length;

            let avgConfidence = '—';
            const confs = dets.filter(d => d.confidence != null).map(d => d.confidence);
            if (confs.length > 0) {
                const mean = confs.reduce((a, b) => a + b, 0) / confs.length;
                avgConfidence = (mean * 100).toFixed(1) + '%';
            }

            this._render({ vessels, tracks, anomalyCount, avgConfidence });
        } catch (err) {
            this._render(DEFAULTS);
        }
    },

    _render(context) {
        this.element.innerHTML = template(context);
    }
};

export default metrics;
