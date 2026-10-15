/**
 * AJAX implementation for materials list using core helpers
 */

window.AppPageLifecycle.onPageLoad(function () {
    const form = document.querySelector('.standard-filter-bar form');
    const materialInput = form?.querySelector('[name="material"]');
    const tipo = form?.querySelector('[name="tipo"]');
    const clearBtn = form?.querySelector('.filter-clear-btn');
    const tableEl = document.getElementById('tablaMateriales');

    if (!form || !tableEl) return;

    const FP = (window.FocusPreserver || {
        save: function(){return{el:document.activeElement,start:document.activeElement&&document.activeElement.selectionStart!==undefined?document.activeElement.selectionStart:null,end:document.activeElement&&document.activeElement.selectionEnd!==undefined?document.activeElement.selectionEnd:null};},
        restore: function(s){if(!s||!s.el)return;try{s.el.focus({preventScroll:true});}catch(_){try{s.el.focus();}catch(__){}}if(s.start!==null&&s.end!==null&&typeof s.el.setSelectionRange==='function'){try{s.el.setSelectionRange(s.start,s.end);}catch(_){}}},
        wrap: function(fn){var s=this.save();var r=fn();if(r&&typeof r.then==='function'){r.then(()=>this.restore(s)).catch(()=>this.restore(s));}else{this.restore(s);}return r;},
        debounce: function(fn,ms){var t=null;return function(){var c=this,a=arguments;if(t)clearTimeout(t);t=setTimeout(function(){fn.apply(c,a);t=null;},ms||350);};}
    });

    const table = AppAjaxTable.init({
        selector: '#tablaMateriales',
        url: tableEl.dataset.apiUrl,
        countSelector: '#materiales-count',
        filters: {
            material: () => materialInput ? materialInput.value.trim() : '',
            tipo: () => tipo ? tipo.value : ''
        },
        columns: [
            {
                data: 'material',
                className: 'py-3 px-4',
                width: '20%',
                render: function (data) {
                    return `<span class="fw-medium">${data}</span>`;
                }
            },
            {
                data: 'marca',
                className: 'py-3 col-marca',
                width: '13%',
                render: function (data) {
                    return `<span class="fw-medium">${data || '-'}</span>`;
                }
            },
            {
                data: 'tipo',
                className: 'py-3 px-4',
                width: '17%',
                render: function (data) {
                    return `<span class="badge badge-tipo">${data || '-'}</span>`;
                }
            },
            {
                data: 'unidad',
                className: 'py-3 px-4 text-center',
                width: '9%'
            },
            {
                data: 'precio',
                className: 'py-3 px-4 text-center fw-medium',
                width: '11%',
                render: function (data) {
                    return `$${data}`;
                }
            },
            {
                data: 'stock',
                className: 'py-3 px-4 text-center',
                width: '8%',
                render: function (data, type, row) {
                    const stock = Number(data) || 0;
                    const minimo = Number(row.stock_minimo) || 0;
                    let clase = 'bg-success-subtle text-success';
                    let titulo = 'Stock disponible';
                    if (stock === 0) {
                        clase = 'bg-danger-subtle text-danger';
                        titulo = 'Sin stock';
                    } else if (stock <= minimo) {
                        clase = 'bg-warning-subtle text-warning';
                        titulo = `Stock bajo (mínimo: ${minimo})`;
                    }
                    return `<span class="badge ${clase}" title="${titulo}">${stock}</span>`;
                }
            },
            {
                data: 'estado',
                className: 'py-3 px-4 text-center',
                width: '7%',
                render: function (data) {
                    const activo = data === 'activo';
                    const color = activo ? '#10b981' : '#64748b';
                    const texto = activo ? 'Activo' : 'Inactivo';
                    return `<span class="d-inline-block rounded-circle" style="width:10px;height:10px;background:${color}" title="${texto}" aria-label="${texto}"></span>`;
                }
            },
            {
                data: 'acciones',
                orderable: false,
                searchable: false,
                className: 'py-3 px-4 text-center',
                width: '15%'
            }
        ],
        emptyText: 'No se encontraron productos'
    });

    if (!table) return;

    const reload = FP.debounce(() => {
        FP.wrap(() => table.ajax.reload());
    }, 300);

    materialInput?.addEventListener('input', reload);
    tipo?.addEventListener('change', () => FP.wrap(() => table.ajax.reload()));

    clearBtn?.addEventListener('click', function (event) {
        event.preventDefault();
        if (materialInput) materialInput.value = '';
        if (tipo) tipo.value = '';
        FP.wrap(() => table.ajax.reload());
    });
});
