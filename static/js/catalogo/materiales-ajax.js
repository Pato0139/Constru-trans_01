/**
 * AJAX implementation for materials list using core helpers
 */

window.AppPageLifecycle.onPageLoad(function () {
    const form = document.querySelector('.standard-filter-bar form');
    const idInput = form?.querySelector('[name="id"]');
    const materialInput = form?.querySelector('[name="material"]');
    const tipo = form?.querySelector('[name="tipo"]');
    const clearBtn = form?.querySelector('.filter-clear-btn');
    const tableEl = document.getElementById('tablaMateriales');

    if (!form || !tableEl) return;

    const FP = window.FocusPreserver;

    const table = AppAjaxTable.init({
        selector: '#tablaMateriales',
        url: tableEl.dataset.apiUrl,
        countSelector: '#materiales-count',
        filters: {
            id: () => idInput ? idInput.value.trim() : '',
            material: () => materialInput ? materialInput.value.trim() : '',
            tipo: () => tipo ? tipo.value : ''
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

    const reload = FP.debounce(() => {
        FP.wrap(() => table.ajax.reload());
    }, 300);

    idInput?.addEventListener('input', reload);
    materialInput?.addEventListener('input', reload);
    tipo?.addEventListener('change', () => FP.wrap(() => table.ajax.reload()));

    clearBtn?.addEventListener('click', function (event) {
        event.preventDefault();
        if (idInput) idInput.value = '';
        if (materialInput) materialInput.value = '';
        if (tipo) tipo.value = '';
        FP.wrap(() => table.ajax.reload());
    });
});
