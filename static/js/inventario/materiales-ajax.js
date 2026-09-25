/**
 * AJAX implementation for materials list using core helpers
 */

document.addEventListener('DOMContentLoaded', function () {
    const form = document.querySelector('.standard-filter-bar form');
    const idInput = form?.querySelector('[name="id"]');
    const materialInput = form?.querySelector('[name="material"]');
    const tipo = form?.querySelector('[name="tipo"]');
    const clearBtn = form?.querySelector('.filter-clear-btn');
    const tableEl = document.getElementById('tablaMateriales');

    if (!form || !tableEl) return;

    const FP = (window.FocusPreserver || {
        save: function(){return{el:document.activeElement,start:document.activeElement&&document.activeElement.selectionStart!==undefined?document.activeElement.selectionStart:null,end:document.activeElement&&document.activeElement.selectionEnd!==undefined?document.activeElement.selectionEnd:null};},
        restore: function(s){if(!s||!s.el)return;try{s.el.focus({preventScroll:true});}catch(_){try{s.el.focus();}catch(__){}}if(s.start!==null&&s.end!==null&&typeof s.el.setSelectionRange==='function'){try{s.el.setSelectionRange(s.start,s.end);}catch(_){}}},
        wrap: function(fn){var s=this.save();var r=fn();if(r&&typeof r.then==='function'){r.then(()=>this.restore(s)).catch(()=>this.restore(s));}else{this.restore(s);}return r;},
        debounce: function(fn,ms){var t=null;return function(){var c=this,a=arguments;if(t)clearTimeout(t);t=setTimeout(function(){fn.apply(c,a);t=null;},ms||350);};
    });

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
