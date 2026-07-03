/**
 * Inicializa las animaciones y efectos de la página de inicio (landing)
 */

// Inicializar Animate On Scroll (AOS)
AOS.init({
    duration: 1200,
    once: true,
    easing: 'ease-out-cubic'
});

/**
 * Cambia el estilo del navbar al hacer scroll
 */
$(window).scroll(function() {
    if ($(this).scrollTop() > 50) {
        $('.navbar-premium').addClass('scrolled');
    } else {
        $('.navbar-premium').removeClass('scrolled');
    }
});
