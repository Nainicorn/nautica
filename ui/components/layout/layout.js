import template from './layout.hbs';
import './layout.css';
import header from '@components/header/header.js';
import sidebar from '@components/sidebar/sidebar.js';
import viewer from '@components/viewer/viewer.js';
import metrics from '@components/metrics/metrics.js';
import alerts from '@components/alerts/alerts.js';
import detections from '@components/detections/detections.js';
import report from '@components/report/report.js';
import upload from '@components/upload/upload.js';

const layout = {
    init() {
        this._render();
        this._initComponents();
    },

    _render() {
        document.body.innerHTML = template();
    },

    _initComponents() {
        header.init();
        sidebar.init();
        viewer.init();
        metrics.init();
        alerts.init();
        detections.init();
        report.init();
        upload.init();
    }
};

export default layout;
