/**
 * Manejador de eventos del navbar para cambiar temas y filtros de daltonismo
 */
document.addEventListener('click', (event) => {
    // Manejar cambio de tema
    const themeLink = event.target.closest('.theme-option');
    if (themeLink) {
        event.preventDefault();
        const theme = themeLink.dataset.themeValue;
        if (typeof setTheme === 'function') setTheme(theme);
        return;
    }

    // Manejar cambio de filtro de daltonismo
    const daltonismLink = event.target.closest('.daltonism-option');
    if (daltonismLink) {
        event.preventDefault();
        const mode = daltonismLink.dataset.daltonismValue;
        if (typeof setDaltonism === 'function') setDaltonism(mode);
    }
});
