
document.addEventListener('click', (event) => {
    const themeLink = event.target.closest('.theme-option');
    if (themeLink) {
        event.preventDefault();
        const theme = themeLink.dataset.themeValue;
        if (typeof setTheme === 'function') setTheme(theme);
        return;
    }

    const daltonismLink = event.target.closest('.daltonism-option');
    if (daltonismLink) {
        event.preventDefault();
        const mode = daltonismLink.dataset.daltonismValue;
        if (typeof setDaltonism === 'function') setDaltonism(mode);
    }
});
