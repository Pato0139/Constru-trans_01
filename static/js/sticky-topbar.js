/**
 * sticky-topbar.js
 * Detecta scroll y añade/quita la clase 'navbar-scrolled' al .app-navbar.
 * Funciona escuchando el scroll del window (NO del main, que no tiene overflow).
 */

(function () {
    'use strict';

    var SCROLL_THRESHOLD = 50;
    var navbar = null;
    var ticking = false;

    /**
     * Aplica o quita la clase navbar-scrolled según la posición del scroll
     */
    function updateNavbar() {
        if (!navbar) return;
        if (window.scrollY > SCROLL_THRESHOLD) {
            navbar.classList.add('navbar-scrolled');
        } else {
            navbar.classList.remove('navbar-scrolled');
        }
        ticking = false;
    }

    /**
     * Handler de scroll con requestAnimationFrame para performance
     */
    function onScroll() {
        if (!ticking) {
            window.requestAnimationFrame(updateNavbar);
            ticking = true;
        }
    }

    /**
     * Inicialización cuando el DOM esté listo
     */
    document.addEventListener('DOMContentLoaded', function () {
        navbar = document.querySelector('.app-navbar');
        if (!navbar) return;

        // Estado inicial (por si ya hubo scroll antes del DOMContentLoaded)
        updateNavbar();

        // Escuchar scroll en window
        window.addEventListener('scroll', onScroll, { passive: true });
    });

})();
