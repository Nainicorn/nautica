import template from './detections.hbs';
import './detections.css';
import { getDetections } from '../../services/analysis.js';
import events from '../../services/events.js';

function confLevel(confidence) {
    if (confidence >= 0.85) return 'high';
    if (confidence >= 0.6) return 'medium';
    return 'low';
}

function statusClass(status) {
    if (status === 'tracking') return 'tracking';
    if (status === 'flagged') return 'alert';
    if (status === 'lost') return 'lost';
    return 'tracking';
}

const detections = {
    element: null,

    init() {
        this.element = document.querySelector('.__detections');
        this._render({ idle: true, badge: '—' });
        events.on('session:selected', (session) => this._load(session.id));
    },

    async _load(sessionId) {
        this._render({ loading: true, badge: '...' });
        try {
            const data = await getDetections(sessionId);
            const items = data.detections.map(d => ({
                ...d,
                confDisplay: d.confidence != null ? (d.confidence * 100).toFixed(1) + '%' : '—',
                confLevel: d.confidence != null ? confLevel(d.confidence) : 'low',
                statusClass: statusClass(d.status),
                statusLabel: (d.status || 'unknown').toUpperCase(),
            }));

            this._render({
                detections: items,
                empty: items.length === 0,
                badge: items.length > 0 ? `${items.length} objects` : '0',
            });
        } catch (err) {
            this._render({ error: true, badge: '—' });
        }
    },

    _render(context) {
        this.element.innerHTML = template(context);
    }
};

export default detections;
