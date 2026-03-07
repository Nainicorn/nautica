import template from './header.hbs';
import './header.css';

const header = {
    element: null,

    init() {
        this._render();
        this._bindListeners();
        this._startClock();
    },

    _render() {
        this.element = document.querySelector('.__header');
        this.element.innerHTML = template();
    },

    _bindListeners() {
        this.element.addEventListener('click', (e) => {
            const $toggle = e.target.closest('.__header-toggle');
            if ($toggle) {
                this._handleToggle();
            }
        });
    },

    _handleToggle() {
        const isCollapsed = document.body.getAttribute('data-collapsed') === 'true';
        document.body.setAttribute('data-collapsed', isCollapsed ? 'false' : 'true');
    },

    _startClock() {
        const $clock = this.element.querySelector('.__header-clock-time');
        const update = () => {
            const now = new Date();
            $clock.textContent = now.toLocaleTimeString('en-US', { hour12: false });
        };
        update();
        setInterval(update, 1000);
    }
};

export default header;
