import template from './upload.hbs';
import './upload.css';
import { createSession, processSession, detectSession, trackSession, analyzeSession } from '../../services/sessions.js';
import { uploadFile } from '../../services/api.js';
import events from '../../services/events.js';

const ALLOWED_EXTENSIONS = ['.mp4', '.mov', '.avi', '.jpg', '.jpeg', '.png'];
const MAX_FILE_SIZE = 200 * 1024 * 1024; // 200MB

const upload = {
    element: null,
    selectedFile: null,
    uploading: false,

    init() {
        this._render();
        this._bindListeners();
    },

    _render() {
        this.element = document.querySelector('.__upload-overlay');
        this.element.innerHTML = template();
    },

    _bindListeners() {
        this.element.addEventListener('click', (e) => {
            const $close = e.target.closest('.__upload-close');
            const $cancel = e.target.closest('.__upload-cancel-btn');
            if (($close || $cancel) && !this.uploading) {
                this.hide();
            }

            const $browse = e.target.closest('.__upload-browse-btn');
            if ($browse) {
                this.element.querySelector('.__upload-file-input').click();
            }

            const $remove = e.target.closest('.__upload-preview-remove');
            if ($remove && !this.uploading) {
                this._clearFile();
            }

            const $submit = e.target.closest('.__upload-submit-btn');
            if ($submit && this.selectedFile && !this.uploading) {
                this._submit();
            }
        });

        // File input change
        this.element.querySelector('.__upload-file-input').addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                this._selectFile(e.target.files[0]);
            }
        });

        // Drag and drop
        const dropzone = this.element.querySelector('.__upload-dropzone');
        dropzone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropzone.classList.add('__upload-dropzone--active');
        });
        dropzone.addEventListener('dragleave', () => {
            dropzone.classList.remove('__upload-dropzone--active');
        });
        dropzone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropzone.classList.remove('__upload-dropzone--active');
            if (e.dataTransfer.files.length > 0) {
                this._selectFile(e.dataTransfer.files[0]);
            }
        });
    },

    _selectFile(file) {
        const ext = '.' + file.name.split('.').pop().toLowerCase();
        if (!ALLOWED_EXTENSIONS.includes(ext)) {
            this._showError(`File type "${ext}" not supported. Use MP4, MOV, AVI, JPG, or PNG.`);
            return;
        }
        if (file.size > MAX_FILE_SIZE) {
            this._showError('File exceeds 200MB limit.');
            return;
        }

        this.selectedFile = file;
        this._hideError();

        // Show preview
        const preview = this.element.querySelector('.__upload-preview');
        const dropzone = this.element.querySelector('.__upload-dropzone');
        preview.style.display = 'block';
        dropzone.style.display = 'none';
        this.element.querySelector('.__upload-preview-name').textContent = file.name;
        this.element.querySelector('.__upload-preview-size').textContent = this._formatSize(file.size);

        // Enable submit
        this.element.querySelector('.__upload-submit-btn').disabled = false;
    },

    _clearFile() {
        this.selectedFile = null;
        const preview = this.element.querySelector('.__upload-preview');
        const dropzone = this.element.querySelector('.__upload-dropzone');
        preview.style.display = 'none';
        dropzone.style.display = 'flex';
        this.element.querySelector('.__upload-file-input').value = '';
        this.element.querySelector('.__upload-submit-btn').disabled = true;
        this._hideError();
    },

    async _submit() {
        if (!this.selectedFile || this.uploading) return;
        this.uploading = true;
        this._hideError();

        const submitBtn = this.element.querySelector('.__upload-submit-btn');
        submitBtn.disabled = true;
        submitBtn.textContent = 'Uploading...';

        const progressEl = this.element.querySelector('.__upload-progress');
        const progressFill = this.element.querySelector('.__upload-progress-fill');
        const progressText = this.element.querySelector('.__upload-progress-text');
        progressEl.style.display = 'flex';

        // Derive session name from filename
        const name = this.selectedFile.name.replace(/\.[^.]+$/, '');
        const ext = '.' + this.selectedFile.name.split('.').pop().toLowerCase();
        const fileType = ['.jpg', '.jpeg', '.png'].includes(ext) ? 'image' : 'video';

        try {
            // 1. Create session
            const session = await createSession(name, fileType);

            // 2. Upload file with progress
            await uploadFile(session.id, this.selectedFile, (pct) => {
                progressFill.style.width = pct + '%';
                progressText.textContent = pct + '%';
            });

            // 3. Upload complete — keep showing upload UI while pipeline runs silently
            progressFill.style.width = '100%';
            progressText.textContent = '100%';
            submitBtn.textContent = 'Processing...';

            await processSession(session.id);
            await detectSession(session.id);
            await trackSession(session.id);
            const analyzed = await analyzeSession(session.id);

            // Close modal and show session — report streams live in the panel
            events.emit('sessions:updated');
            events.emit('session:selected', { ...analyzed, _live: true });
            events.emit('report:stream', analyzed.id);
            this.hide();
        } catch (err) {
            this._showError('Upload failed: ' + err.message);
            submitBtn.textContent = 'Start Analysis';
            submitBtn.disabled = false;
            progressEl.style.display = 'none';
            progressFill.style.width = '0%';
        } finally {
            this.uploading = false;
        }
    },

    _showError(msg) {
        const el = this.element.querySelector('.__upload-error');
        el.textContent = msg;
        el.style.display = 'block';
    },

    _hideError() {
        const el = this.element.querySelector('.__upload-error');
        el.textContent = '';
        el.style.display = 'none';
    },

    _formatSize(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    },

    show() {
        this._reset();
        this.element.style.display = 'flex';
    },

    hide() {
        this.element.style.display = 'none';
        this._reset();
    },

    _reset() {
        this.selectedFile = null;
        this.uploading = false;
        const preview = this.element.querySelector('.__upload-preview');
        const dropzone = this.element.querySelector('.__upload-dropzone');
        const progressEl = this.element.querySelector('.__upload-progress');
        const submitBtn = this.element.querySelector('.__upload-submit-btn');

        if (preview) preview.style.display = 'none';
        if (dropzone) dropzone.style.display = 'flex';
        if (progressEl) progressEl.style.display = 'none';
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.textContent = 'Start Analysis';
        }

        const fileInput = this.element.querySelector('.__upload-file-input');
        if (fileInput) fileInput.value = '';

        this._hideError();
    }
};

export default upload;
