/**
 * Generic AJAX DataTable initialization helper
 */
window.AppAjaxTable = (() => {
    function init(config) {
        const {
            selector,
            url,
            filters = {},
            columns = [],
            countSelector = null,
            pageLength = 10,
            emptyText = 'No se encontraron registros'
        } = config;

        if (typeof $ === 'undefined' || !$.fn.DataTable) return null;

        const table = $(selector);
        if (!table.length) return null;

        return table.DataTable({
            processing: true,
            serverSide: true,
            responsive: true,
            searching: false,
            ordering: false,
            pageLength,
            lengthMenu: [10, 25, 50],
            ajax: {
                url,
                data(d) {
                    Object.entries(filters).forEach(([key, getter]) => {
                        d[key] = typeof getter === 'function' ? getter() : getter;
                    });
                },
                dataSrc(json) {
                    if (countSelector) {
                        const el = document.querySelector(countSelector);
                        if (el) el.textContent = `${json.recordsFiltered} registros`;
                    }
                    return json.data;
                },
                error() {
                    AppHTTP.showError('No se pudieron cargar los datos de la tabla');
                }
            },
            language: {
                processing: 'Cargando...',
                zeroRecords: emptyText,
                info: 'Mostrando _START_ a _END_ de _TOTAL_ registros',
                infoEmpty: 'No hay registros disponibles',
                infoFiltered: '(filtrado de _MAX_ registros)',
                lengthMenu: 'Mostrar _MENU_ registros',
                paginate: {
                    first: 'Primero',
                    last: 'Último',
                    next: 'Siguiente',
                    previous: 'Anterior'
                }
            },
            dom: '<"d-flex justify-content-between align-items-center flex-wrap gap-3 mt-3 px-3"l>rt<"d-flex justify-content-between align-items-center flex-wrap gap-3 mt-3 px-3 pb-3"ip>',
            columns
        });
    }

    return { init };
})();
