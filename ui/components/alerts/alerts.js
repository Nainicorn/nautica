import template from './alerts.hbs';
import './alerts.css';
import { getAnomalies } from '../../services/analysis.js';
import events from '../../services/events.js';

function timeAgo(isoString) {
    if (!isoString) return '';
    const diffMs = Date.now() - new Date(isoString).getTime();
    const minutes = Math.floor(diffMs / 60000);
    if (minutes < 1) return 'just now';
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    return `${days}d ago`;
}

const alerts = {
    element: null,

    init() {
        this.element = document.querySelector('.__alerts');
        this._render({ idle: true, count: '—' });
        events.on('session:selected', (session) => this._load(session.id));
    },

    async _load(sessionId) {
        this._render({ loading: true, count: '...' });
        try {
            const data = await getAnomalies(sessionId);
            const items = data.anomalies.map(a => ({
                ...a,
                severity: a.severity || 'info',
                timeAgo: timeAgo(a.created_at),
            }));

            this._render({
                anomalies: items,
                empty: items.length === 0,
                count: items.length,
            });
        } catch (err) {
            this._render({ error: true, count: '—' });
        }
    },

    _render(context) {
        this.element.innerHTML = template(context);
    }
};

export default alerts;
