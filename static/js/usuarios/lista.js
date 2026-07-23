/**
 * @file Gestión de pestañas de lista de usuarios con sincronización de estado
 */

/**
 * Inicializa eventos de pestañas y sincronización de URL
 * @listens DOMContentLoaded
 */
document.addEventListener('DOMContentLoaded', function() {
    /**
     * Manejador de clic en pestañas para actualizar estado activo
     */
    document.querySelectorAll('#userTabs .nav-link').forEach(tabBtn => {
        tabBtn.addEventListener('click', function() {
            const tabName = this.id.replace('-tab', '');
            updateActiveTab(tabName);
        });
    });

    /**
     * Restaura la pestaña activa desde parámetros URL al cargar la página
     */
    const params = new URLSearchParams(window.location.search);
    const activeTab = params.get('tab');
    if (activeTab) {
        const tabEl = document.querySelector(`#${activeTab}-tab`);
        if (tabEl) {
            const tab = new bootstrap.Tab(tabEl);
            tab.show();
        }
    }
});

/**
 * Actualiza el estado de la pestaña activa y sincroniza con URL
 * @param {string} tabName - Nombre de la pestaña activa
 */
function updateActiveTab(tabName) {
    // Actualizar el input oculto del formulario de búsqueda
    const activeTabInput = document.getElementById('activeTabInput');
    if (activeTabInput) {
        activeTabInput.value = tabName;
    }
    
    // Opcional: Actualizar la URL sin recargar la página para que si el usuario copia el link, mantenga la pestaña
    const url = new URL(window.location);
    url.searchParams.set('tab', tabName);
    window.history.pushState({}, '', url);

    /**
     * Recalcula dimensiones de DataTables para tablas ocultas/visibles
     */
    setTimeout(() => {
        $.fn.dataTable.tables({ visible: true, api: true }).columns.adjust();
    }, 100);
}
