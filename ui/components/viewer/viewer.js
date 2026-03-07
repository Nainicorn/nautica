import template from './viewer.hbs';
import './viewer.css';

const viewer = {
    element: null,

    init() {
        this._render();
    },

    _render() {
        this.element = document.querySelector('.__viewer');
        this.element.innerHTML = template();
    }
};

export default viewer;
