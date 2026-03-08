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
    if (status === 'tracked') return 'tracking';
    if (status === 'flagged') return 'alert';
    if (status === 'lost') return 'lost';
    return 'tracking';
}


const detections = {
    element: null,
    allItems: [],
    visibleCount: 0,
    currentFrame: 0,
    seenTracks: new Set(),
    liveMode: false,
    $tbody: null,
    $badge: null,

    init() {
        this.element = document.querySelector('.__detections');
        this._render({ idle: true, badge: '—' });
        events.on('session:selected', (session) => this._load(session.id, session._live));
        events.on('viewer:frame-changed', (frameNum) => this._onFrameChanged(frameNum));
    },

    async _load(sessionId, live) {
        this._render({ loading: true, badge: '...' });
        this.allItems = [];
        this.visibleCount = 0;
        this.currentFrame = 0;
        this.seenTracks = new Set();
        this.liveMode = !!live;

        try {
            const data = await getDetections(sessionId);
            this.allItems = data.detections.map(d => ({
                ...d,
                confDisplay: d.confidence != null ? (d.confidence * 100).toFixed(1) + '%' : '—',
                confLevel: d.confidence != null ? confLevel(d.confidence) : 'low',
                statusClass: statusClass(d.status),
                statusLabel: (d.status || 'unknown').toUpperCase(),
            }));

            if (!this.liveMode) {
                // Static mode — show all unique tracks immediately
                const seen = new Set();
                const uniqueItems = [];
                for (const item of this.allItems) {
                    const key = item.track_id || item.id;
                    if (!seen.has(key)) {
                        seen.add(key);
                        uniqueItems.push(item);
                    }
                }
                this._render({
                    streaming: uniqueItems.length > 0,
                    empty: uniqueItems.length === 0,
                    badge: `${uniqueItems.length} vessels`,
                });
                this.$tbody = this.element.querySelector('.__detections-tbody');
                if (this.$tbody) {
                    this.$tbody.innerHTML = uniqueItems.map(i => this._buildRow(i)).join('');
                }
                this._bindRowClick();
                return;
            }

            // Live mode — render empty shell, rows appear as video plays
            this._render({
                detections: [],
                empty: this.allItems.length === 0,
                badge: this.allItems.length > 0 ? '0 objects' : '0',
                streaming: this.allItems.length > 0,
            });

            this.$tbody = this.element.querySelector('.__detections-tbody');
            this.$badge = this.element.querySelector('.__detections-badge');
            this._bindRowClick();
        } catch (err) {
            this._render({ empty: true, badge: '0' });
        }
    },

    _bindRowClick() {
        if (!this.$tbody) return;
        this.$tbody.addEventListener('click', (e) => {
            const row = e.target.closest('tr[data-frame]');
            if (!row) return;
            const frameNum = parseInt(row.dataset.frame, 10);
            if (!isNaN(frameNum)) {
                events.emit('detection:seek', frameNum);
            }
        });
    },

    _onFrameChanged(frameNum) {
        if (!this.liveMode || !this.allItems.length || !this.$tbody) return;
        if (frameNum < this.currentFrame) {
            this.$tbody.innerHTML = '';
            this.visibleCount = 0;
            this.seenTracks = new Set();
        }
        this.currentFrame = frameNum;

        while (this.visibleCount < this.allItems.length) {
            const item = this.allItems[this.visibleCount];
            if (item.frame_number != null && item.frame_number > frameNum) break;
            const key = item.track_id || item.id;
            if (!this.seenTracks.has(key)) {
                this.seenTracks.add(key);
                this.$tbody.insertAdjacentHTML('beforeend', this._buildRow(item));
            }
            this.visibleCount++;
        }

        if (this.$badge) {
            this.$badge.textContent = `${this.seenTracks.size} vessels`;
        }
    },

    _buildRow(item) {
        const frameAttr = item.frame_number != null ? `data-frame="${item.frame_number}"` : '';
        return `<tr class="__detections-row--new __detections-row--clickable" ${frameAttr}>
            <td class="__detections-id">${item.track_id || '—'}</td>
            <td>${item.vessel_size || item.object_type || '—'}</td>
            <td><span class="__detections-conf __detections-conf--${item.confLevel}">${item.confDisplay}</span></td>
            <td class="__detections-mono">${item.position || '—'}</td>
            <td><span class="__detections-status __detections-status--${item.statusClass}">${item.statusLabel}</span></td>
        </tr>`;
    },

    _render(context) {
        this.element.innerHTML = template(context);
    }
};

export default detections;
