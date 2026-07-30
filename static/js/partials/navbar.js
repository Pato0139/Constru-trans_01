/**
 * Manejador de eventos del navbar para cambiar temas y filtros de daltonismo
 */
function closeAccessibilityMenus() {
    document.querySelectorAll('.js-accessibility-dropdown').forEach((dropdown) => {
        const toggle = dropdown.querySelector('[data-bs-toggle="dropdown"]');
        if (toggle && window.bootstrap?.Dropdown) {
            window.bootstrap.Dropdown.getOrCreateInstance(toggle).hide();
        }
    });
}

document.addEventListener('click', (event) => {
    // Manejar cambio de tema
    const themeLink = event.target.closest('.theme-option');
    if (themeLink) {
        event.preventDefault();
        const theme = themeLink.dataset.themeValue;
        if (typeof setTheme === 'function') setTheme(theme);
        closeAccessibilityMenus();
        return;
    }

    // Manejar cambio de filtro de daltonismo
    const daltonismLink = event.target.closest('.daltonism-option');
    if (daltonismLink) {
        event.preventDefault();
        const mode = daltonismLink.dataset.daltonismValue;
        if (typeof setDaltonism === 'function') setDaltonism(mode);
        closeAccessibilityMenus();
        return;
    }

    // Cierra el menú al pulsar fuera del bloque de accesibilidad.
    if (!event.target.closest('.js-accessibility-dropdown')) {
        closeAccessibilityMenus();
    }
});
