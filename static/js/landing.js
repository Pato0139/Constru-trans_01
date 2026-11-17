/**
 * Inicializa las animaciones, scroll suave y efectos de la página de inicio (landing)
 */

// 1. Inicializar Animate On Scroll (AOS)
if (window.AOS) {
    AOS.init({
        duration: 1200,
        once: true,
        easing: 'ease-out-cubic'
    });
}

// 2. Control de estilo scrolled para el navbar
function updateNavbarScroll() {
    const navbar = document.querySelector('.navbar-premium');
    if (!navbar) return;
    if (window.scrollY > 50) {
        navbar.classList.add('scrolled');
    } else {
        navbar.classList.remove('scrolled');
    }
}

window.addEventListener('scroll', updateNavbarScroll, { passive: true });
updateNavbarScroll();

// 3. Desplazamiento suave para enlaces de anclaje (#inicio, #nosotros, #servicios, #contacto)
function initLandingSmoothScroll() {
    // Seleccionar todos los enlaces que contengan un hash relativo en navbar y landing
    const anchorLinks = document.querySelectorAll('.navbar-premium a[href*="#"], .hero-premium a[href*="#"]');
    const navbarCollapse = document.getElementById('navbarPremiumContent');

    anchorLinks.forEach(function (link) {
        if (link.dataset.smoothScrollBound === 'true') return;
        link.dataset.smoothScrollBound = 'true';

        link.addEventListener('click', function (e) {
            const rawHref = this.getAttribute('href');
            if (!rawHref || rawHref === '#' || !rawHref.includes('#')) return;

            const hash = rawHref.substring(rawHref.indexOf('#'));
            if (!hash || hash === '#') return;

            // Buscar elemento destino (con soporte para alias #modulos / #servicios)
            let target = document.querySelector(hash);
            if (!target && hash === '#servicios') {
                target = document.querySelector('#modulos');
            } else if (!target && hash === '#modulos') {
                target = document.querySelector('#servicios');
            }

            if (target) {
                e.preventDefault();

                // Si estamos en móvil y el menú hamburguesa está abierto, cerrarlo
                if (navbarCollapse && navbarCollapse.classList.contains('show')) {
                    if (window.bootstrap && window.bootstrap.Collapse) {
                        const bsCollapse = window.bootstrap.Collapse.getInstance(navbarCollapse) ||
                            new window.bootstrap.Collapse(navbarCollapse, { toggle: false });
                        bsCollapse.hide();
                    } else {
                        navbarCollapse.classList.remove('show');
                    }
                }

                // Calcular altura actual de la navbar fija para compensar el offset
                const navbar = document.querySelector('.navbar-premium');
                const navHeight = navbar ? navbar.offsetHeight : 80;

                const targetPosition = target.getBoundingClientRect().top + window.pageYOffset;
                const offsetPosition = Math.max(0, targetPosition - navHeight - 12);

                window.scrollTo({
                    top: offsetPosition,
                    behavior: 'smooth'
                });

                // Actualizar la URL sin saltos bruscos
                if (window.history && window.history.pushState) {
                    window.history.pushState(null, null, hash);
                }
            }
        });
    });

    // Logo / Marca: click para volver suavemente arriba si estamos en la landing
    const brand = document.querySelector('.landing-navbar-brand');
    if (brand && !brand.dataset.brandScrollBound) {
        brand.dataset.brandScrollBound = 'true';
        brand.addEventListener('click', function (e) {
            if (window.location.pathname === '/' || window.location.pathname.endsWith('/inicio/')) {
                const inicioSection = document.getElementById('inicio');
                if (inicioSection) {
                    e.preventDefault();
                    window.scrollTo({ top: 0, behavior: 'smooth' });
                    if (window.history && window.history.pushState) {
                        window.history.pushState(null, null, window.location.pathname);
                    }
                }
            }
        });
    }

    // 4. Indicador visual de la sección activa según el scroll (ScrollSpy ligero)
    const sections = [
        { id: 'inicio', nav: document.querySelector('.navbar-nav a[href$="#inicio"]') },
        { id: 'nosotros', nav: document.querySelector('.navbar-nav a[href$="#nosotros"]') },
        { id: 'servicios', nav: document.querySelector('.navbar-nav a[href$="#servicios"]') || document.querySelector('.navbar-nav a[href$="#modulos"]') },
        { id: 'contacto', nav: document.querySelector('.navbar-nav a[href$="#contacto"]') },
    ].filter(function (item) {
        return Boolean(document.getElementById(item.id) || (item.id === 'servicios' && document.getElementById('modulos')));
    });

    function updateActiveNavLink() {
        const scrollY = window.pageYOffset || document.documentElement.scrollTop || 0;
        const navbar = document.querySelector('.navbar-premium');
        const navHeight = navbar ? navbar.offsetHeight : 80;

                    // Por defecto en la parte superior la sección activa siempre es 'inicio'
                    let currentSectionId = 'inicio';

                    // Si el usuario llega al final del scroll de la página, activar 'contacto'
                    const isBottom = (window.innerHeight + scrollY) >= (document.documentElement.scrollHeight - 60);
                    if (isBottom) {
                        currentSectionId = 'contacto';
                    } else {
                        // Recorrer las secciones usando coordenadas absolutas del documento (getBoundingClientRect)
                        sections.forEach(function (item) {
                            const el = document.getElementById(item.id) || (item.id === 'servicios' ? document.getElementById('modulos') : null);
                            if (el) {
                                const rect = el.getBoundingClientRect();
                                const docTop = rect.top + scrollY;
                                if (scrollY >= docTop - navHeight - 120) {
                                    currentSectionId = item.id;
                                }
                            }
            });
                }

                sections.forEach(function (item) {
                    if (item.nav) {
                        if (item.id === currentSectionId) {
                            item.nav.classList.add('active');
                        } else {
                            item.nav.classList.remove('active');
                        }
                    }
                });
            }

            window.addEventListener('scroll', updateActiveNavLink, { passive: true });
            updateActiveNavLink();
        }

        // Inicializar cuando el DOM esté listo
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', initLandingSmoothScroll);
        } else {
            initLandingSmoothScroll();
        }

        // Integración con ciclo de vida SPA si aplica
        if (window.AppPageLifecycle && typeof window.AppPageLifecycle.onPageLoad === 'function') {
            window.AppPageLifecycle.onPageLoad(initLandingSmoothScroll);
        }
