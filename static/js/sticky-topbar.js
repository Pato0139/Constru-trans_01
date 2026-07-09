/**
 * @file Sistema de topbar sticky con animación de reducción al hacer scroll
 * @description Aplica comportamiento sticky a todos los headers del dashboard con transiciones suaves
 */

/**
 * Inicializa el comportamiento sticky para todos los topbars del dashboard
 * @listens DOMContentLoaded
 * @listens scroll
 */
document.addEventListener('DOMContentLoaded', () => {
    const navbar = document.querySelector('.app-navbar');
    const contentHeaders = document.querySelectorAll('.content-header, [class*="header"]:not(.app-navbar):not(header.navbar-premium)');
    
    let lastScrollY = window.scrollY;
    let ticking = false;

    /**
     * Aplica las clases de scroll al navbar
     * @param {number} scrollY - Posición actual del scroll
     */
    function updateNavbar(scrollY) {
        if (!navbar) return;

        if (scrollY > 50) {
            navbar.classList.add('navbar-scrolled');
        } else {
            navbar.classList.remove('navbar-scrolled');
        }
    }

    /**
     * Aplica las clases de scroll a los content headers
     * @param {number} scrollY - Posición actual del scroll
     */
    function updateContentHeaders(scrollY) {
        contentHeaders.forEach(header => {
            if (scrollY > 50) {
                header.classList.add('header-scrolled');
            } else {
                header.classList.remove('header-scrolled');
            }
        });
    }

    /**
     * Handler optimizado con requestAnimationFrame
     */
    function handleScroll() {
        lastScrollY = window.scrollY;

        if (!ticking) {
            window.requestAnimationFrame(() => {
                updateNavbar(lastScrollY);
                updateContentHeaders(lastScrollY);
                ticking = false;
            });

            ticking = true;
        }
    }

    // Aplicar estado inicial
    updateNavbar(window.scrollY);
    updateContentHeaders(window.scrollY);

    // Escuchar el evento scroll
    window.addEventListener('scroll', handleScroll, { passive: true });

    // Aplicar sticky a cualquier header dinámicamente agregado
    const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            mutation.addedNodes.forEach((node) => {
                if (node.nodeType === 1) {
                    const newHeaders = node.querySelectorAll('.content-header, [class*="header"]:not(.app-navbar)');
                    if (newHeaders.length > 0) {
                        updateContentHeaders(window.scrollY);
                    }
                }
            });
        });
    });

    observer.observe(document.body, { childList: true, subtree: true });
});
