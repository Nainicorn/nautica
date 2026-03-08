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

const TRICKLE_DELAY_MS = 800;

const alerts = {
    element: null,
    _trickleTimer: null,

    init() {
        this.element = document.querySelector('.__alerts');
        this._render({ idle: true, count: '—' });
        events.on('session:selected', (session) => this._load(session.id, session._live));
    },

    _clearTrickle() {
        if (this._trickleTimer) {
            clearTimeout(this._trickleTimer);
            this._trickleTimer = null;
        }
    },

    async _load(sessionId, live) {
        this._clearTrickle();
        this._render({ loading: true, count: '...' });
        try {
            const data = await getAnomalies(sessionId);
            const items = (data.anomalies || []).map(a => ({
                ...a,
                severity: a.severity || 'info',
                timeAgo: timeAgo(a.created_at),
            }));

            if (!live || items.length === 0) {
                this._render({
                    anomalies: items,
                    empty: items.length === 0,
                    count: items.length,
                });
                return;
            }

            // Live mode — trickle alerts in one at a time
            this._render({ anomalies: [], empty: false, count: 0 });
            this._trickleItems(items, 0);
        } catch (err) {
            this._render({ empty: true, count: 0 });
        }
    },

    _trickleItems(items, index) {
        if (index >= items.length) return;
        const shown = items.slice(0, index + 1);
        this._render({ anomalies: shown, empty: false, count: shown.length });
        this._trickleTimer = setTimeout(() => {
            this._trickleItems(items, index + 1);
        }, TRICKLE_DELAY_MS);
    },

    _render(context) {
        this.element.innerHTML = template(context);
    }
};

export default alerts;
