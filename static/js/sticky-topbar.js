/**
 * sticky-topbar.js
 * Mantiene la barra superior fija y estable durante el desplazamiento.
 */
(function () {
    'use strict';

    document.addEventListener('DOMContentLoaded', function () {
        var navbar = document.querySelector('.app-navbar');
        if (navbar) navbar.classList.remove('navbar-scrolled');
    });
})();
