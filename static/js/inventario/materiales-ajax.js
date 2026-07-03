/**
 * AJAX implementation for materials list using core helpers
 */

document.addEventListener('DOMContentLoaded', function () {
    const inputBusqueda = document.getElementById('busquedaMateriales');
    const filtroTipo = document.getElementById('filtroTipoMaterial');
    const formFiltros = document.getElementById('filtrosMaterialesForm');

    const table = AppAjaxTable.init({
        selector: '#tablaMateriales',
        url: document.getElementById('tablaMateriales').dataset.apiUrl,
        countSelector: '#materiales-count',
        filters: {
            tipo: () => filtroTipo ? filtroTipo.value : '',
            'search[value]': () => inputBusqueda ? inputBusqueda.value.trim() : ''
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

    if (inputBusqueda) {
        inputBusqueda.addEventListener('input', AppHTTP.debounce(() => table.ajax.reload(), 300));
    }

    if (filtroTipo) {
        filtroTipo.addEventListener('change', () => table.ajax.reload());
    }

    if (formFiltros) {
        formFiltros.addEventListener('submit', function (event) {
            event.preventDefault();
            table.ajax.reload();
        });
    }
});
