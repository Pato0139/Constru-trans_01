/**
 * AJAX implementation for materials list using core helpers
 */

document.addEventListener('DOMContentLoaded', function () {
    const form = document.querySelector('.standard-filter-bar form');
    const tipo = form?.querySelector('[name="tipo"]');
    const query = form?.querySelector('[name="q"]');
    const clearBtn = form?.querySelector('.filter-clear-btn');
    const tableEl = document.getElementById('tablaMateriales');

    if (!form || !tableEl) return;

    const table = AppAjaxTable.init({
        selector: '#tablaMateriales',
        url: tableEl.dataset.apiUrl,
        countSelector: '#materiales-count',
        filters: {
            tipo: () => tipo ? tipo.value : '',
            q: () => query ? query.value.trim() : ''
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
                    return `<span class="fw-medium">${data}</span>`;
                }
            },
            {
                data: 'tipo',
                className: 'py-3 px-4',
                render: function (data) {
                    return `<span class="badge badge-tipo">${data || '-'}</span>`;
                }
            },
            {
                data: 'unidad',
                className: 'py-3 px-4 text-center'
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

    const reload = AppHTTP.debounce(() => table.ajax.reload(), 300);

    tipo?.addEventListener('change', reload);
    query?.addEventListener('input', reload);

    clearBtn?.addEventListener('click', function (event) {
        event.preventDefault();
        if (tipo) tipo.value = '';
        if (query) query.value = '';
        table.ajax.reload();
    });
});
