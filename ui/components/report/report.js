import template from './report.hbs';
import './report.css';
import { getReport, getReportStreamUrl } from '../../services/analysis.js';
import events from '../../services/events.js';

function formatTimestamp(isoString) {
    if (!isoString) return '--:--:--';
    const d = new Date(isoString);
    return d.toLocaleString([], {
        month: 'short', day: 'numeric',
        hour: '2-digit', minute: '2-digit',
    });
}

const CHAR_DELAY_MS = 6;

const report = {
    element: null,
    _eventSource: null,
    _charBuffer: '',
    _charTimer: null,
    _streaming: false,

    init() {
        this.element = document.querySelector('.__report');
        this._render({ idle: true, timestamp: '--:--:--' });
        events.on('session:selected', (session) => {
            this._closeStream();
            if (session._live) {
                // Live session — report will arrive via report:stream event
                this._render({ idle: true, timestamp: 'Awaiting report...' });
                return;
            }
            this._load(session.id);
        });
        events.on('report:stream', (sessionId) => this._stream(sessionId));
    },

    async _load(sessionId) {
        this._render({ loading: true, timestamp: '...' });
        try {
            const data = await getReport(sessionId);
            const hasContent = data.summary || data.anomalies_text || data.recommendation;

            const isDemo = data.summary && data.summary.startsWith('[DEMO MODE]');
            this._render({
                ...data,
                demoMode: isDemo,
                empty: !hasContent,
                timestamp: formatTimestamp(data.generated_at),
            });
        } catch (err) {
            this._render({ empty: true, timestamp: '--:--:--' });
        }
    },

    _stream(sessionId) {
        this._closeStream();
        this._streaming = true;

        // Render the streaming shell with cursor
        this._render({ streaming: true, timestamp: 'Generating...' });
        const textEl = this.element.querySelector('.__report-stream-text');
        const cursorEl = this.element.querySelector('.__report-cursor');

        const url = getReportStreamUrl(sessionId);
        const eventSource = new EventSource(url);
        this._eventSource = eventSource;

        let streamDone = false;
        let streamError = false;
        let connectionDead = false;

        const drainBuffer = () => {
            if (this._charBuffer.length > 0) {
                textEl.textContent += this._charBuffer[0];
                this._charBuffer = this._charBuffer.slice(1);
                const body = this.element.querySelector('.__report-body');
                body.scrollTop = body.scrollHeight;
                this._charTimer = setTimeout(drainBuffer, CHAR_DELAY_MS);
            } else if (streamDone) {
                this._charTimer = null;
                this._closeStream();
                const tsEl = this.element.querySelector('.__report-timestamp');
                if (tsEl) tsEl.textContent = 'Generated: ' + formatTimestamp(new Date().toISOString());
                if (cursorEl) cursorEl.remove();
                events.emit('sessions:updated');
            } else if (streamError) {
                this._charTimer = null;
                this._closeStream();
                if (!textEl.textContent.trim()) {
                    textEl.textContent = '[Report generation failed]';
                }
                if (cursorEl) cursorEl.remove();
            } else if (connectionDead) {
                // Connection closed without done/error — treat as successful if we have text
                this._charTimer = null;
                this._closeStream();
                if (textEl.textContent.trim()) {
                    const tsEl = this.element.querySelector('.__report-timestamp');
                    if (tsEl) tsEl.textContent = 'Generated: ' + formatTimestamp(new Date().toISOString());
                    events.emit('sessions:updated');
                }
                if (cursorEl) cursorEl.remove();
            } else {
                // Buffer empty but stream still going — wait for more
                this._charTimer = setTimeout(drainBuffer, CHAR_DELAY_MS);
            }
        };

        eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.text) {
                this._charBuffer += data.text;
                if (!this._charTimer) drainBuffer();
            }
            if (data.done) streamDone = true;
            if (data.error) streamError = true;
        };

        eventSource.onerror = () => {
            if (this._eventSource) {
                this._eventSource.close();
                this._eventSource = null;
            }
            // If stream already delivered done, drainBuffer will finish naturally
            if (streamDone) return;
            // Mark connection as dead — drainBuffer will handle cleanup
            // after a grace period for any remaining onmessage events
            setTimeout(() => { connectionDead = true; }, 100);
        };
    },

    _closeStream() {
        this._streaming = false;
        if (this._eventSource) {
            this._eventSource.close();
            this._eventSource = null;
        }
        if (this._charTimer) {
            clearTimeout(this._charTimer);
            this._charTimer = null;
        }
        this._charBuffer = '';
    },

    _render(context) {
        this.element.innerHTML = template(context);
    }
};

export default report;
