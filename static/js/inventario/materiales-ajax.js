/**
 * AJAX implementation for materials list using core helpers
 */

document.addEventListener('DOMContentLoaded', function () {
    const inputId = document.getElementById('filtroId');
    const inputMaterial = document.getElementById('filtroMaterial');
    const filtroTipo = document.getElementById('filtroTipoMaterial');
    const formFiltros = document.getElementById('filtrosMaterialesForm');
    const btnLimpiar = document.getElementById('btnLimpiarFiltros');

    const table = AppAjaxTable.init({
        selector: '#tablaMateriales',
        url: document.getElementById('tablaMateriales').dataset.apiUrl,
        countSelector: '#materiales-count',
        filters: {
            tipo: () => filtroTipo ? filtroTipo.value : '',
            material: () => inputMaterial ? inputMaterial.value.trim() : '',
            id: () => inputId ? inputId.value.trim() : ''
        },
        columns: [
            {
                data: 'id',
                className: 'py-3 px-4 text-center fw-bold',
                render: function (data) {
                    return `#${data}`;
                }
            },
            {
                data: 'material',
                className: 'py-3 px-4',
                render: function (data) {
                    const inicial = data ? data.charAt(0).toUpperCase() : '-';
                    return `
                        <div class="d-flex align-items-center gap-3">
                            <div class="bg-accent rounded-circle d-flex align-items-center justify-content-center fw-bold text-dark ui-w-35 ui-h-35">
                                ${inicial}
                            </div>
                            <span class="fw-medium">${data}</span>
                        </div>
                    `;
                }
            },
            {
                data: 'tipo',
                className: 'py-3 px-4',
                render: function (data) {
                    return `<span class="badge bg-dark text-white-50 border border-white-10">${data || '-'}</span>`;
                }
            },
            {
                data: 'unidad',
                className: 'py-3 px-4 text-center'
            },
            {
                data: 'stock',
                className: 'py-3 px-4 text-center'
            },
            {
                data: 'precio',
                className: 'py-3 px-4 text-center fw-bold ui-text-accent'
            },
            {
                data: 'acciones',
                orderable: false,
                searchable: false,
                className: 'py-3 px-4 text-center'
            }
        ],
        emptyText: 'No se encontraron materiales'
    });

    if (!table) return;

    if (!table) return;

    function checkActiveFilters() {
        if (btnLimpiar) {
            const hasFilters = (inputId && inputId.value.trim()) || 
                               (inputMaterial && inputMaterial.value.trim()) || 
                               (filtroTipo && filtroTipo.value);
            btnLimpiar.style.display = hasFilters ? 'inline-block' : 'none';
        }
    }

    const reloadTable = AppHTTP.debounce(() => {
        table.ajax.reload();
        checkActiveFilters();
    }, 300);

    if (inputId) inputId.addEventListener('input', reloadTable);
    if (inputMaterial) inputMaterial.addEventListener('input', reloadTable);
    if (filtroTipo) filtroTipo.addEventListener('change', reloadTable);

    if (formFiltros) {
        formFiltros.addEventListener('submit', function (event) {
            event.preventDefault();
            table.ajax.reload();
            checkActiveFilters();
        });
    }

    if (btnLimpiar) {
        btnLimpiar.addEventListener('click', function() {
            if (inputId) inputId.value = '';
            if (inputMaterial) inputMaterial.value = '';
            if (filtroTipo) filtroTipo.value = '';
            table.ajax.reload();
            checkActiveFilters();
        });
    }
});
