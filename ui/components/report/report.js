import template from './report.hbs';
import './report.css';
import { getReport } from '../../services/analysis.js';
import events from '../../services/events.js';

function formatTimestamp(isoString) {
    if (!isoString) return '--:--:--';
    const d = new Date(isoString);
    return d.toLocaleString([], {
        month: 'short', day: 'numeric',
        hour: '2-digit', minute: '2-digit',
    });
}

const report = {
    element: null,

    init() {
        this.element = document.querySelector('.__report');
        this._render({ idle: true, timestamp: '--:--:--' });
        events.on('session:selected', (session) => this._load(session.id));
    },

    async _load(sessionId) {
        this._render({ loading: true, timestamp: '...' });
        try {
            const data = await getReport(sessionId);
            const hasContent = data.summary || data.anomalies_text || data.recommendation;

            this._render({
                ...data,
                empty: !hasContent,
                timestamp: formatTimestamp(data.generated_at),
            });
        } catch (err) {
            this._render({ error: true, timestamp: '--:--:--' });
        }
    },

    _render(context) {
        this.element.innerHTML = template(context);
    }
};

export default report;
