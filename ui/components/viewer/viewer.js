import template from './viewer.hbs';
import './viewer.css';
import events from '../../services/events.js';
import { getOverlayData, getFrameUrl } from '../../services/playback.js';

const PRELOAD_AHEAD = 12;
const KEEP_BEHIND = 8;

const PLAYBACK_STATUSES = [
    'extracted', 'detecting', 'detection_complete',
    'tracking', 'tracking_complete',
    'anomaly_detection', 'anomaly_complete',
    'generating_report', 'report_complete',
];

const viewer = {
    element: null,
    sessionId: null,
    overlayData: null,
    currentFrameIndex: 0,
    isPlaying: false,
    showOverlay: true,
    fps: 5,
    frameCache: new Map(),
    animFrameId: null,
    lastFrameTime: 0,
    resizeObserver: null,

    // DOM refs
    $container: null,
    $canvasContainer: null,
    $frame: null,
    $canvas: null,
    $ctx: null,
    $loading: null,
    $playBtn: null,
    $timecode: null,
    $progressBar: null,
    $progress: null,
    $overlayBtn: null,
    $speedLabel: null,
    $progressHandle: null,
    _dragging: false,
    _wasPlaying: false,

    init() {
        this.element = document.querySelector('.__viewer');
        this.element.innerHTML = template();
        this._cacheDOM();
        this._bindListeners();
    },

    _cacheDOM() {
        const el = this.element;
        this.$container = el.querySelector('.__viewer-container');
        this.$canvasContainer = el.querySelector('.__viewer-canvas-container');
        this.$frame = el.querySelector('.__viewer-frame');
        this.$canvas = el.querySelector('.__viewer-canvas');
        this.$ctx = this.$canvas.getContext('2d');
        this.$loading = el.querySelector('.__viewer-loading');
        this.$playBtn = el.querySelector('.__viewer-btn-play');
        this.$timecode = el.querySelector('.__viewer-timecode');
        this.$progressBar = el.querySelector('.__viewer-progress-bar');
        this.$progress = el.querySelector('.__viewer-progress');
        this.$overlayBtn = el.querySelector('.__viewer-btn-overlay');
        this.$speedLabel = el.querySelector('.__viewer-speed-label');
        this.$progressHandle = el.querySelector('.__viewer-progress-handle');
    },

    _bindListeners() {
        events.on('session:selected', (session) => this._loadSession(session));
        events.on('detection:seek', (frameNum) => this._seekToFrame(frameNum));

        this.$playBtn.addEventListener('click', () => {
            this.isPlaying ? this._pause() : this._play();
        });

        this.element.querySelector('.__viewer-btn-step-back')
            .addEventListener('click', () => this._stepBack());

        this.element.querySelector('.__viewer-btn-step-forward')
            .addEventListener('click', () => this._stepForward());

        this.$progress.addEventListener('click', (e) => {
            if (this._dragging) return;
            const rect = this.$progress.getBoundingClientRect();
            const fraction = (e.clientX - rect.left) / rect.width;
            this._seek(fraction);
        });

        this.$progressHandle.addEventListener('mousedown', (e) => {
            e.preventDefault();
            this._dragging = true;
            this._wasPlaying = this.isPlaying;
            if (this.isPlaying) this._pause();
            this.$progressHandle.classList.add('__viewer-progress-handle--dragging');

            const onMove = (e) => {
                const rect = this.$progress.getBoundingClientRect();
                const fraction = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
                if (!this.overlayData || !this.overlayData.frames.length) return;
                const index = Math.round(fraction * (this.overlayData.frames.length - 1));
                this._displayFrame(index);
                this._preloadFrames(index);
            };

            const onUp = () => {
                this._dragging = false;
                this.$progressHandle.classList.remove('__viewer-progress-handle--dragging');
                document.removeEventListener('mousemove', onMove);
                document.removeEventListener('mouseup', onUp);
                if (this._wasPlaying) this._play();
            };

            document.addEventListener('mousemove', onMove);
            document.addEventListener('mouseup', onUp);
        });

        this.$overlayBtn.addEventListener('click', () => {
            this.showOverlay = !this.showOverlay;
            this.$overlayBtn.classList.toggle('__viewer-control-btn--active', this.showOverlay);
            this._renderCurrentFrame();
        });

        this.$frame.addEventListener('load', () => {
            this._alignCanvas();
            if (this.showOverlay) {
                this._drawOverlay(this._currentFrameNumber());
            }
            this.$loading.classList.add('__viewer-loading--hidden');
        });

        this.resizeObserver = new ResizeObserver(() => {
            if (this.overlayData) this._alignCanvas();
        });
        this.resizeObserver.observe(this.$canvasContainer);
    },

    _reset() {
        if (this.animFrameId) {
            cancelAnimationFrame(this.animFrameId);
            this.animFrameId = null;
        }
        this.isPlaying = false;
        this.currentFrameIndex = 0;
        this.frameCache.clear();
        this.overlayData = null;
        this.sessionId = null;
        this.$playBtn.querySelector('.material-icon').textContent = 'play_arrow';
        this.$ctx.clearRect(0, 0, this.$canvas.width, this.$canvas.height);
        this.$frame.src = '';
    },

    async _loadSession(session) {
        if (!session || !PLAYBACK_STATUSES.includes(session.status)) {
            this._reset();
            this.$container.classList.remove('__viewer-container--active', '__viewer-container--single');
            return;
        }

        this._reset();
        this.sessionId = session.id;
        this.$container.classList.add('__viewer-container--active');
        this.$loading.classList.remove('__viewer-loading--hidden');

        try {
            this.overlayData = await getOverlayData(session.id);
            this.fps = this.overlayData.playback_target_fps || 5;
            this.$speedLabel.textContent = `${this.fps} FPS`;

            const isSingle = this.overlayData.frames.length <= 1;
            this.$container.classList.toggle('__viewer-container--single', isSingle);

            this._preloadFrames(0);
            this._displayFrame(0);
            if (!isSingle) this._play();

        } catch (err) {
            console.error('Failed to load overlay data:', err);
            this.$loading.classList.add('__viewer-loading--hidden');
        }
    },

    _currentFrameNumber() {
        if (!this.overlayData || !this.overlayData.frames.length) return 0;
        return this.overlayData.frames[this.currentFrameIndex].frame_number;
    },

    _displayFrame(index) {
        if (!this.overlayData || !this.overlayData.frames.length) return;
        index = Math.max(0, Math.min(index, this.overlayData.frames.length - 1));
        this.currentFrameIndex = index;

        const frameNum = this._currentFrameNumber();
        const url = getFrameUrl(this.sessionId, frameNum);

        const cached = this.frameCache.get(frameNum);
        if (cached && cached.complete) {
            this.$frame.src = cached.src;
        } else {
            this.$frame.src = url;
        }

        this._updateTimecode();
        this._updateProgress();
        events.emit('viewer:frame-changed', frameNum);
    },

    _renderCurrentFrame() {
        if (this.showOverlay) {
            this._drawOverlay(this._currentFrameNumber());
        } else {
            this.$ctx.clearRect(0, 0, this.$canvas.width, this.$canvas.height);
        }
    },

    _alignCanvas() {
        const img = this.$frame;
        if (!img.naturalWidth || !img.naturalHeight) return;

        const container = this.$canvasContainer;
        const cw = container.clientWidth;
        const ch = container.clientHeight;
        const nw = img.naturalWidth;
        const nh = img.naturalHeight;

        const scale = Math.min(cw / nw, ch / nh);
        const renderedW = nw * scale;
        const renderedH = nh * scale;
        const offsetX = (cw - renderedW) / 2;
        const offsetY = (ch - renderedH) / 2;

        this.$canvas.width = renderedW;
        this.$canvas.height = renderedH;
        this.$canvas.style.left = `${offsetX}px`;
        this.$canvas.style.top = `${offsetY}px`;
        this.$canvas.style.width = `${renderedW}px`;
        this.$canvas.style.height = `${renderedH}px`;
    },

    _drawOverlay(frameNum) {
        const ctx = this.$ctx;
        const canvas = this.$canvas;
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        if (!this.overlayData || !this.$frame.naturalWidth) return;

        const frameData = this.overlayData.frames[this.currentFrameIndex];
        if (!frameData || !frameData.detections.length) return;

        const nw = this.$frame.naturalWidth;
        const nh = this.$frame.naturalHeight;
        const scaleX = canvas.width / nw;
        const scaleY = canvas.height / nh;

        ctx.strokeStyle = '#19C2C9';
        ctx.lineWidth = 2;
        ctx.font = '11px "JetBrains Mono", monospace';

        for (const det of frameData.detections) {
            const x = det.bbox.x * scaleX;
            const y = det.bbox.y * scaleY;
            const w = det.bbox.width * scaleX;
            const h = det.bbox.height * scaleY;

            // Bounding box
            ctx.strokeRect(x, y, w, h);

            // Label
            const label = this._buildLabel(det);
            const textMetrics = ctx.measureText(label);
            const labelH = 16;
            const labelW = textMetrics.width + 8;
            const labelY = y - labelH - 2;

            // Label background
            ctx.fillStyle = 'rgba(10, 18, 32, 0.85)';
            ctx.fillRect(x, labelY < 0 ? y : labelY, labelW, labelH);

            // Label text
            ctx.fillStyle = '#FFFFFF';
            ctx.fillText(label, x + 4, (labelY < 0 ? y : labelY) + 12);
        }
    },

    _buildLabel(det) {
        const parts = [];
        if (det.track_id) parts.push(det.track_id);
        if (det.vessel_size) parts.push(det.vessel_size);
        else if (det.object_type) parts.push(det.object_type);
        if (det.confidence != null) parts.push(`${Math.round(det.confidence * 100)}%`);
        return parts.join(' ');
    },

    _play() {
        if (!this.overlayData || this.overlayData.frames.length <= 1) return;
        if (this.currentFrameIndex >= this.overlayData.frames.length - 1) {
            this.currentFrameIndex = 0;
            this._displayFrame(0);
            this._preloadFrames(0);
        }
        this.isPlaying = true;
        this.$playBtn.querySelector('.material-icon').textContent = 'pause';
        this.lastFrameTime = performance.now();
        this._tick();
    },

    _pause() {
        this.isPlaying = false;
        if (this.animFrameId) {
            cancelAnimationFrame(this.animFrameId);
            this.animFrameId = null;
        }
        this.$playBtn.querySelector('.material-icon').textContent = 'play_arrow';
    },

    _tick() {
        if (!this.isPlaying) return;

        this.animFrameId = requestAnimationFrame((now) => {
            const elapsed = now - this.lastFrameTime;
            const interval = 1000 / this.fps;

            if (elapsed >= interval) {
                this.lastFrameTime = now - (elapsed % interval);
                const nextIndex = this.currentFrameIndex + 1;

                if (nextIndex >= this.overlayData.frames.length) {
                    this._pause();
                    return;
                }

                this._displayFrame(nextIndex);
                this._preloadFrames(nextIndex);
            }

            this._tick();
        });
    },

    _stepForward() {
        this._pause();
        if (!this.overlayData) return;
        const next = Math.min(this.currentFrameIndex + 1, this.overlayData.frames.length - 1);
        this._displayFrame(next);
        this._preloadFrames(next);
    },

    _stepBack() {
        this._pause();
        if (!this.overlayData) return;
        const prev = Math.max(this.currentFrameIndex - 1, 0);
        this._displayFrame(prev);
    },

    _seek(fraction) {
        this._pause();
        if (!this.overlayData || !this.overlayData.frames.length) return;
        const index = Math.round(fraction * (this.overlayData.frames.length - 1));
        this._displayFrame(index);
        this._preloadFrames(index);
    },

    _seekToFrame(frameNum) {
        if (!this.overlayData || !this.overlayData.frames.length) return;
        const index = this.overlayData.frames.findIndex(f => f.frame_number >= frameNum);
        if (index === -1) return;
        this._pause();
        this._displayFrame(index);
        this._preloadFrames(index);
    },

    _preloadFrames(fromIndex) {
        if (!this.overlayData) return;
        const frames = this.overlayData.frames;

        // Preload ahead
        const end = Math.min(fromIndex + PRELOAD_AHEAD, frames.length);
        for (let i = fromIndex; i < end; i++) {
            const fn = frames[i].frame_number;
            if (!this.frameCache.has(fn)) {
                const img = new Image();
                img.src = getFrameUrl(this.sessionId, fn);
                this.frameCache.set(fn, img);
            }
        }

        // Evict frames too far behind
        const keepFrom = Math.max(fromIndex - KEEP_BEHIND, 0);
        for (let i = 0; i < keepFrom; i++) {
            const fn = frames[i].frame_number;
            this.frameCache.delete(fn);
        }
    },

    _updateTimecode() {
        if (!this.overlayData) return;
        const current = this.currentFrameIndex + 1;
        const total = this.overlayData.frames.length;
        this.$timecode.textContent = `Frame ${current} / ${total}`;
    },

    _updateProgress() {
        if (!this.overlayData || !this.overlayData.frames.length) return;
        const pct = ((this.currentFrameIndex) / (this.overlayData.frames.length - 1)) * 100;
        const clamped = Math.min(pct, 100);
        this.$progressBar.style.width = `${clamped}%`;
        this.$progressHandle.style.left = `${clamped}%`;
    },
};

export default viewer;
