document.addEventListener('DOMContentLoaded', function() {
    // Tab click handlers
    document.querySelectorAll('#userTabs .nav-link').forEach(tabBtn => {
        tabBtn.addEventListener('click', function() {
            const tabName = this.id.replace('-tab', '');
            updateActiveTab(tabName);
        });
    });

    // Al cargar la página, asegurarse de que la pestaña correcta esté activa si viene por URL
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

    // Recalcular DataTables si es necesario (evita problemas de ancho en tablas ocultas)
    setTimeout(() => {
        $.fn.dataTable.tables({ visible: true, api: true }).columns.adjust();
    }, 100);
}
