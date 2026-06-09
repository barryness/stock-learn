/* ============================================================
   utils.js — Shared utility functions (global: window.Utils)
   ============================================================ */

(function() {
    const U = {};

    U.debounce = function(fn, delay = 300) {
        let timer;
        return function (...args) {
            clearTimeout(timer);
            timer = setTimeout(() => fn.apply(this, args), delay);
        };
    };

    U.throttle = function(fn, limit = 100) {
        let inThrottle;
        return function (...args) {
            if (!inThrottle) {
                fn.apply(this, args);
                inThrottle = true;
                setTimeout(() => { inThrottle = false; }, limit);
            }
        };
    };

    U.slugify = function(text) {
        return text.toLowerCase().replace(/[^\w一-鿿]+/g, '-').replace(/^-+|-+$/g, '');
    };

    U.escapeHtml = function(str) {
        const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
        return str.replace(/[&<>"']/g, c => map[c]);
    };

    U.closest = function(el, selector) {
        while (el && el !== document) {
            if (el.matches && el.matches(selector)) return el;
            el = el.parentNode;
        }
        return null;
    };

    U.storeSet = function(key, value) {
        try { localStorage.setItem('stock_learn_' + key, JSON.stringify(value)); } catch {}
    };

    U.storeGet = function(key, fallback = null) {
        try {
            const v = localStorage.getItem('stock_learn_' + key);
            return v !== null ? JSON.parse(v) : fallback;
        } catch { return fallback; }
    };

    window.Utils = U;
})();
