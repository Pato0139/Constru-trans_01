/**
 * sticky-topbar.js
 * Detecta scroll en window Y en .main-content,
 * añade/quita clase 'navbar-scrolled' al .app-navbar.
 */
(function () {
    'use strict';

    var SCROLL_THRESHOLD = 50;
    var navbar = null;
    var mainEl = null;
    var ticking = false;

    function getScrollY() {
        if (mainEl) return mainEl.scrollTop;
        return window.scrollY || window.pageYOffset || 0;
    }

    function updateNavbar() {
        if (!navbar) return;
        if (getScrollY() > SCROLL_THRESHOLD) {
            navbar.classList.add('navbar-scrolled');
        } else {
            navbar.classList.remove('navbar-scrolled');
        }
        ticking = false;
    }

    function onScroll() {
        if (!ticking) {
            window.requestAnimationFrame(updateNavbar);
            ticking = true;
        }
    }

    document.addEventListener('DOMContentLoaded', function () {
        navbar = document.querySelector('.app-navbar');
        mainEl = document.querySelector('.main-content');
        if (!navbar) return;

        updateNavbar();

        window.addEventListener('scroll', onScroll, { passive: true });
        if (mainEl) {
            mainEl.addEventListener('scroll', onScroll, { passive: true });
        }
    });
})();
