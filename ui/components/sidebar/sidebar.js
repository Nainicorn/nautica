import template from './sidebar.hbs';
import './sidebar.css';
import { getSessions, deleteSession } from '../../services/sessions.js';
import events from '../../services/events.js';
import upload from '../upload/upload.js';

function formatDate(isoString) {
    if (!isoString) return '';
    const date = new Date(isoString);
    const now = new Date();
    const diffMs = now - date;
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) {
        return 'Today ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
    if (diffDays === 1) return 'Yesterday';
    return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
}

function badgeForStatus(status) {
    if (status === 'uploading') {
        return { badgeClass: 'active', badgeLabel: 'UPLOADING' };
    }
    if (status === 'uploaded') {
        return { badgeClass: 'pending', badgeLabel: 'UPLOADED' };
    }
    if (status === 'processing' || status === 'detecting' || status === 'tracking') {
        return { badgeClass: 'active', badgeLabel: 'PROCESSING' };
    }
    if (status === 'extracted') {
        return { badgeClass: 'pending', badgeLabel: 'READY' };
    }
    if (status === 'completed') {
        return { badgeClass: 'complete', badgeLabel: 'DONE' };
    }
    if (status === 'failed') {
        return { badgeClass: 'error', badgeLabel: 'FAIL' };
    }
    return { badgeClass: 'pending', badgeLabel: 'PENDING' };
}

const sidebar = {
    element: null,
    sessions: [],
    activeSessionId: null,

    init() {
        this.element = document.querySelector('.__sidebar');
        this._render({ loading: true });
        this._loadSessions();
        this._bindListeners();
        events.on('sessions:updated', () => this._loadSessions());
    },

    async _loadSessions() {
        try {
            this._render({ loading: true });
            const data = await getSessions();
            this.sessions = data.sessions;
            this._renderSessions();
        } catch (err) {
            this._render({ error: true });
        }
    },

    _renderSessions() {
        const sessions = this.sessions.map(s => ({
            ...s,
            active: s.id === this.activeSessionId,
            date: formatDate(s.created_at),
            ...badgeForStatus(s.status),
        }));

        this._render({
            sessions,
            empty: sessions.length === 0,
        });
    },

    _render(context) {
        this.element.innerHTML = template(context);
    },

    _bindListeners() {
        this.element.addEventListener('click', async (e) => {
            const $newBtn = e.target.closest('.__sidebar-new-btn');
            if ($newBtn) {
                upload.show();
                return;
            }

            const $deleteBtn = e.target.closest('.__sidebar-session-delete');
            if ($deleteBtn) {
                const deleteId = $deleteBtn.dataset.deleteId;
                if (!deleteId) return;
                try {
                    await deleteSession(deleteId);
                    if (this.activeSessionId === deleteId) {
                        this.activeSessionId = null;
                    }
                    this._loadSessions();
                } catch (err) {
                    console.error('Failed to delete session:', err);
                }
                return;
            }

            const $session = e.target.closest('.__sidebar-session');
            if (!$session) return;

            const sessionId = $session.dataset.sessionId;
            const session = this.sessions.find(s => s.id === sessionId);
            if (!session || session.id === this.activeSessionId) return;

            this.activeSessionId = sessionId;
            this._renderSessions();
            events.emit('session:selected', session);
        });

        events.on('session:selected', (session) => {
            if (session && session.id) {
                this.activeSessionId = session.id;
                this._renderSessions();
            }
        });
    }
};

export default sidebar;
