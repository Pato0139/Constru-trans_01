(function (global) {
    function _isManagedByMaterialesAjax(form) {
        if (!form) return false;
        const matTable = document.getElementById('tablaMateriales');
        if (!matTable) return false;
        const container = form.closest('.inventory-materials-container, .inventory-materials-page, main') || document;
        return container.contains(matTable);
    }

    function findTargetTbody(form) {
        if (!form) return null;
        const tbodyId = form.dataset.tbodyId;
        if (tbodyId) {
            const byId = document.getElementById(tbodyId);
            if (byId) return byId;
        }
        const scopes = [
            form.closest('.table-container'),
            form.closest('.inventory-materials-container'),
            form.closest('.tab-pane'),
            form.closest('.container-fluid'),
            form.closest('main'),
            document,
        ];
        for (let i = 0; i < scopes.length; i++) {
            const scope = scopes[i];
            if (!scope) continue;
            const tables = scope.querySelectorAll('table');
            for (let j = 0; j < tables.length; j++) {
                const t = tables[j];
                if (t.id === 'tablaMateriales') continue;
                const tb = t.querySelector('tbody');
                if (tb) return tb;
            }
        }
        return null;
    }

    function isAjaxRequest(form) {
        if (!form || form.dataset.noAjaxFilter === 'true') return false;
        if (_isManagedByMaterialesAjax(form)) return false;
        const ajaxFlag = form.dataset.ajaxFilterForm;
        if (ajaxFlag === 'true' || ajaxFlag === '1') return true;
        return Boolean(findTargetTbody(form));
    }

    function _replaceTbodySafe(tbody, newInnerHtml) {
        const tableEl = tbody ? tbody.closest('table') : null;
        const hasDT = Boolean(
            tableEl &&
            global.$ &&
            global.$.fn &&
            global.$.fn.dataTable &&
            global.$.fn.dataTable.isDataTable(tableEl)
        );
        let savedPageLength = 10;
        if (hasDT) {
            try {
                const dt = global.$(tableEl).DataTable();
                savedPageLength = dt.page.len() || 10;
                dt.destroy();
            } catch (_) {}
        }

        tbody.innerHTML = newInnerHtml;

        if (hasDT && tableEl && !tableEl.classList.contains('no-datatable')) {
            try {
                global.$(tableEl).DataTable({
                    language: {
                        search: 'Buscar:',
                        lengthMenu: 'Mostrar _MENU_ registros por página',
                        zeroRecords: 'No se encontraron resultados',
                        info: 'Mostrando registros del _START_ al _END_ de un total de _TOTAL_ registros',
                        infoEmpty: 'No hay registros disponibles',
                        infoFiltered: '(filtrado de _MAX_ registros totales)',
                        paginate: {
                            first: 'Primero',
                            last: 'Último',
                            next: 'Siguiente',
                            previous: 'Anterior',
                        },
                    },
                    pageLength: savedPageLength,
                    responsive: true,
                    dom: '<"d-flex justify-content-between align-items-center flex-wrap gap-3 mb-3"l>rt<"d-flex justify-content-between align-items-center flex-wrap gap-3 mt-4"ip>',
                });
            } catch (_) {}
        }
    }

    function saveFocus() {
        const activeEl = document.activeElement;
        return {
            el: activeEl || null,
            id: activeEl ? activeEl.id : null,
            name: activeEl ? activeEl.name : null,
            className: activeEl && activeEl.className && typeof activeEl.className === 'string' ? activeEl.className : null,
            tagName: activeEl ? activeEl.tagName : null,
            formRef: activeEl && activeEl.form ? activeEl.form : null,
            start: activeEl && activeEl.selectionStart !== undefined ? activeEl.selectionStart : null,
            end: activeEl && activeEl.selectionEnd !== undefined ? activeEl.selectionEnd : null,
            value: activeEl && activeEl.value !== undefined ? activeEl.value : null,
        };
    }

    function restoreFocus(saved, scopeForm) {
        if (!saved) return;
        let target = null;
        if (saved.id) target = document.getElementById(saved.id);
        if (!target && saved.name && scopeForm) {
            target = scopeForm.querySelector('[name="' + saved.name + '"]');
        }
        if (!target && saved.name && saved.formRef) {
            try {
                const candidates = saved.formRef.querySelectorAll('[name="' + saved.name + '"]');
                if (candidates && candidates.length) {
                    for (let i = 0; i < candidates.length; i++) {
                        const c = candidates[i];
                        if (!saved.tagName || c.tagName === saved.tagName) {
                            target = c;
                            break;
                        }
                    }
                }
            } catch (_) {}
        }
        if (!target && saved.el && document.body.contains(saved.el)) {
            target = saved.el;
        }
        if (!target && saved.name) {
            const allByName = document.querySelectorAll('[name="' + saved.name + '"]');
            if (allByName && allByName.length) {
                for (let j = 0; j < allByName.length; j++) {
                    const c2 = allByName[j];
                    if (saved.tagName && c2.tagName !== saved.tagName) continue;
                    if (saved.value !== null && typeof c2.value !== 'undefined' && c2.value === saved.value) {
                        target = c2;
                        break;
                    }
                    if (!target) target = c2;
                }
            }
        }
        if (target && typeof target.focus === 'function') {
            try { target.focus({ preventScroll: true }); }
            catch (_) { try { target.focus(); } catch (__) {} }
            if (saved.start !== null && saved.end !== null && typeof target.setSelectionRange === 'function') {
                try { target.setSelectionRange(saved.start, saved.end); } catch (_) {}
            }
        }
    }

    function withFocusPreservation(fn, scopeForm) {
        const saved = saveFocus();
        let result;
        try {
            result = (typeof fn === 'function') ? fn() : fn;
        } finally {
            if (result && typeof result.then === 'function') {
                result.then(function () { restoreFocus(saved, scopeForm); })
                      .catch(function () { restoreFocus(saved, scopeForm); });
            } else {
                restoreFocus(saved, scopeForm);
            }
        }
        return result;
    }

    function debounce(fn, ms) {
        let t = null;
        return function () {
            const ctx = this, args = arguments;
            if (t) clearTimeout(t);
            t = setTimeout(function () { fn.apply(ctx, args); t = null; }, ms);
        };
    }

    global.FocusPreserver = {
        save: saveFocus,
        restore: restoreFocus,
        wrap: withFocusPreservation,
        debounce: debounce,
    };

    function bindStandardAutoFilter(form) {
        if (!form || form.dataset.autoBindDone === '1') return;
        if (_isManagedByMaterialesAjax(form)) return;
        form.dataset.autoBindDone = '1';

        const useAjax = isAjaxRequest(form);
        const tbody = findTargetTbody(form);
        const DEBOUNCE_MS = 320;

        let timer = null;
        let currentQueryString = window.location.search || '';
        let abortController = null;

        const fields = form.querySelectorAll('input.filter-input, select.filter-select, input[name="q"], select[name]');

        function buildUrl() {
            const formData = new FormData(form);
            const params = new URLSearchParams();
            let hasAny = false;
            for (const [k, v] of formData.entries()) {
                if (v !== '' && v !== null && v !== undefined) {
                    params.append(k, v);
                    hasAny = true;
                }
            }
            const baseUrl = form.getAttribute('action') || window.location.pathname;
            const qs = hasAny ? '?' + params.toString() : '';
            return { full: baseUrl + qs, qs: qs, base: baseUrl };
        }

        function reinjectTooltips() {
            if (typeof global.initAppTooltips === 'function') {
                global.initAppTooltips();
            } else if (global.bootstrap && typeof global.bootstrap.Tooltip !== 'undefined') {
                document.querySelectorAll('[data-tooltip], [data-bs-toggle="tooltip"]').forEach((el) => {
                    try { new global.bootstrap.Tooltip(el); } catch (_) {}
                });
            }
        }

        async function applyAjaxFilter() {
            if (timer) { clearTimeout(timer); timer = null; }
            const { full, qs } = buildUrl();
            if (qs === currentQueryString) return;
            currentQueryString = qs;

            const savedFocus = saveFocus();

            if (abortController) abortController.abort();
            abortController = new AbortController();

            if (tbody) {
                tbody.style.opacity = '0.45';
                tbody.style.transition = 'opacity 120ms ease';
            }

            try {
                const res = await fetch(full, {
                    method: 'GET',
                    headers: { 'X-Requested-With': 'XMLHttpRequest' },
                    credentials: 'same-origin',
                    signal: abortController.signal,
                });
                if (!res.ok) throw new Error('Status ' + res.status);
                const html = await res.text();
                if (tbody) {
                    if (typeof global.cleanupOrphanTooltips === 'function') {
                        global.cleanupOrphanTooltips();
                    } else {
                        document.querySelectorAll('.tooltip').forEach((t) => t.remove());
                    }
                    if (html.includes('<!DOCTYPE') || html.includes('<html')) {
                        try {
                            const parser = new DOMParser();
                            const doc = parser.parseFromString(html, 'text/html');
                            const matchedTbody = (tbody.id ? doc.getElementById(tbody.id) : null) || doc.querySelector('tbody');
                            if (matchedTbody) {
                                _replaceTbodySafe(tbody, matchedTbody.innerHTML);
                                // Actualizar paginación si existe
                                const curPag = document.querySelector('nav[aria-label="Paginación"]');
                                const newPag = doc.querySelector('nav[aria-label="Paginación"]');
                                if (curPag && newPag) {
                                    curPag.innerHTML = newPag.innerHTML;
                                } else if (curPag && !newPag) {
                                    curPag.innerHTML = '';
                                }
                            } else {
                                window.location.href = full;
                                return;
                            }
                        } catch (_) {
                            _replaceTbodySafe(tbody, html);
                        }
                    } else {
                        _replaceTbodySafe(tbody, html);
                    }
                }
                const currentSearch = window.location.search || '';
                if (qs === currentSearch) {
                    history.replaceState(null, '', full);
                } else {
                    history.pushState(null, '', full);
                }
                reinjectTooltips();
                if (typeof form.dataset.onAfterUpdate === 'string' && form.dataset.onAfterUpdate && global[form.dataset.onAfterUpdate]) {
                    try { global[form.dataset.onAfterUpdate](html); } catch (_) {}
                }
            } catch (err) {
                if (err.name === 'AbortError') return;
                console.warn('Error en filtro AJAX:', err);
                if (tbody) {
                    window.location.href = buildUrl().full;
                    return;
                }
            } finally {
                if (tbody) tbody.style.opacity = '';
                restoreFocus(savedFocus, form);
            }
        }

        function submitFullPage() {
            if (timer) { clearTimeout(timer); timer = null; }
            const { qs } = buildUrl();
            if (qs === currentQueryString) return;
            currentQueryString = qs;
            if (form.requestSubmit) form.requestSubmit(); else form.submit();
        }

        function scheduleApply() {
            if (timer) clearTimeout(timer);
            timer = setTimeout(useAjax ? applyAjaxFilter : submitFullPage, DEBOUNCE_MS);
        }

        function immediateApply() {
            useAjax ? applyAjaxFilter() : submitFullPage();
        }

        fields.forEach((field) => {
            const tag = field.tagName;
            if (tag === 'SELECT') {
                field.addEventListener('change', immediateApply);
            } else if (tag === 'INPUT') {
                const type = (field.type || 'text').toLowerCase();
                if (type === 'date' || type === 'number') {
                    field.addEventListener('change', immediateApply);
                }
                field.addEventListener('input', scheduleApply);
            }
        });

        form.addEventListener('submit', function (e) {
            if (useAjax) {
                e.preventDefault();
                applyAjaxFilter();
            }
        });

        // Interceptar botón "Limpiar filtros" para limpiar y recargar solo la tabla sin refrescar toda la página
        const clearLink =
            form.querySelector('.filter-clear-btn, .ct-clear-btn') ||
            (form.closest('.filter-bar-card') && form.closest('.filter-bar-card').querySelector('a.filter-clear-btn, a.ct-clear-btn'));
        if (clearLink && useAjax && clearLink.tagName === 'A') {
            clearLink.addEventListener('click', function (e) {
                e.preventDefault();
                fields.forEach(function (field) {
                    if (field.tagName === 'SELECT' || field.tagName === 'INPUT') {
                        field.value = '';
                        if (field.tagName === 'SELECT') {
                            field.dispatchEvent(new Event('change', { bubbles: false }));
                        }
                    }
                });
                _updateClearBtnState(form, clearLink);
                applyAjaxFilter();
            });
        }

        global.addEventListener('popstate', function () {
            if (!form.isConnected) return;
            currentQueryString = window.location.search || '';
            const sp = new URLSearchParams(window.location.search);
            fields.forEach((field) => {
                const name = field.name;
                if (!name) return;
                const val = sp.get(name);
                if (val !== null) field.value = val;
                else if (field.tagName === 'SELECT' || field.tagName === 'INPUT') field.value = '';
            });
            if (useAjax) applyAjaxFilter(); else submitFullPage();
        });
    }

    /* =====================================================================
       Mejora visual automática para todas las barras de filtro (.filter-bar-card)
       - Agrega íconos dentro de cada campo sin duplicar sus placeholders
       - Decora el filtro desplegable de estado con un indicador semántico
       - Mejora el botón "Limpiar filtros" y soporta limpieza instantánea por AJAX
       ===================================================================== */
    function _inferFieldMeta(el) {
        const name = (el.getAttribute('name') || el.id || '').toLowerCase();
        const tag = el.tagName;
        const type = (el.getAttribute('type') || '').toLowerCase();

        let icon = 'bi-search';
        if (type === 'date') icon = 'bi-calendar3';
        else if (name.includes('estado')) icon = 'bi-sliders2';
        else if (name.includes('vehiculo') || name.includes('placa') || name.includes('tipo_vehiculo')) icon = 'bi-truck';
        else if (name.includes('cliente') || name.includes('usuario') || name.includes('conductor')) icon = 'bi-person';
        else if (name.includes('rol')) icon = 'bi-shield-check';
        else if (name.includes('categoria') || name.includes('tipo') || name.includes('marca')) icon = 'bi-tags';
        else if (name.includes('proveedor')) icon = 'bi-building';
        else if (name.includes('direccion') || name.includes('destino')) icon = 'bi-geo-alt';
        else if (tag === 'SELECT') icon = 'bi-funnel';

        return { icon: icon };
    }

    function _inferDotClass(value, text) {
        const s = ((value || '') + ' ' + (text || '')).toLowerCase();
        if (!value) return '';
        if (/(inactivo|inactiva|cancelado|rechazado|suspendido|bloqueado|salida|bajo|agotado|incidente|fallid|vencid|indisponible|no disponible)/.test(s)) {
            return 'ct-dot--red';
        }
        if (/(disponible|activo|activa|entregado|completado|aprobado|pagado|entrada|resuelt|cerrad|autorizado|verificado)/.test(s)) {
            return 'ct-dot--green';
        }
        if (/(ruta|camino|proceso|asignado|en_transito|transito|admin|conductor)/.test(s)) {
            return 'ct-dot--blue';
        }
        if (/(mantenimiento|pendiente|revision|revisión|correccion|corrección|abiert|espera|cliente|parcial)/.test(s)) {
            return 'ct-dot--amber';
        }
        return 'ct-dot--slate';
    }

    function _updateClearBtnState(form, clearBtn) {
        if (!form || !clearBtn) return;
        const inputs = form.querySelectorAll('input:not([type="hidden"]):not([type="submit"]), select');
        let hasActive = false;
        inputs.forEach(function (el) {
            if ((el.value || '').trim() !== '') hasActive = true;
        });
        clearBtn.classList.toggle('has-active-filters', hasActive);
    }

    /* =====================================================================
       Validación de caracteres por tipo de campo en filtros
       - digits  : solo números (N.° pedido, ID, documento, teléfono)
       - nit     : números y guion (NIT)
       - letters : solo letras y espacios (nombres, clientes, ciudades, conductores)
       - alnum   : letras, números y guion (placas, códigos, licencias)
       - address : letras, números y signos de dirección (# . , - /)
       ===================================================================== */
    const _FILTER_REGEX = {
        digits: /[^0-9]/g,
        nit: /[^0-9-]/g,
        letters: /[^a-zA-ZáéíóúÁÉÍÓÚñÑüÜ\s]/g,
        alnum: /[^a-zA-Z0-9\s-]/g,
        address: /[^a-zA-ZáéíóúÁÉÍÓÚñÑüÜ0-9\s#.,°/-]/g,
    };

    function _inferInputRule(el) {
        if (!el || el.tagName !== 'INPUT') return null;
        const type = (el.getAttribute('type') || 'text').toLowerCase();
        if (type !== 'text' && type !== 'search') return null;

        const explicit = (el.dataset.filterRule || '').trim().toLowerCase();
        if (explicit && _FILTER_REGEX[explicit]) return explicit;

        const name = (el.getAttribute('name') || el.id || '').toLowerCase();
        const ph = (el.getAttribute('placeholder') || '').toLowerCase();

        // 1. Solo números
        if (
            name === 'id' ||
            name === 'id_pedido' ||
            name === 'id_vehiculo' ||
            name === 'documento' ||
            name === 'telefono' ||
            ph.startsWith('n.° pedido') ||
            ph.startsWith('id ') ||
            ph === 'id' ||
            ph === 'documento' ||
            ph === 'teléfono'
        ) {
            return 'digits';
        }
        if (name === 'nit' || ph === 'nit') {
            return 'nit';
        }

        // 2. Solo letras y espacios (nombres, clientes, ciudades, conductores, tipo texto)
        if (
            name === 'cliente' ||
            name === 'ciudad' ||
            name === 'nombre' ||
            name === 'conductor' ||
            name === 'tipo' ||
            name === 'categoria' ||
            ph.includes('ciudad') ||
            ph.startsWith('cliente') ||
            ph.startsWith('nombre') ||
            ph.startsWith('conductor') ||
            ph.startsWith('tipo de vehículo')
        ) {
            return 'letters';
        }

        // 3. Placas, códigos, licencias (alfanumérico)
        if (
            name === 'vehiculo' ||
            name === 'licencia' ||
            name === 'codigo' ||
            (name === 'placa' && !ph.includes('conductor')) ||
            ph.startsWith('placa') ||
            ph.startsWith('licencia') ||
            ph.startsWith('código')
        ) {
            return 'alnum';
        }

        // 4. Direcciones / destinos / ubicaciones
        if (
            name === 'destino' ||
            name === 'direccion' ||
            name === 'ubicacion' ||
            ph.startsWith('dirección') ||
            ph.startsWith('destino') ||
            ph.startsWith('ubicación')
        ) {
            return 'address';
        }

        return null;
    }

    function _attachInputSanitizer(el) {
        if (!el || el.dataset.ctSanitizerBound === '1') return;
        const rule = _inferInputRule(el);
        if (!rule) return;

        el.dataset.ctSanitizerBound = '1';
        el.dataset.filterRule = rule;
        if (rule === 'digits' || rule === 'nit') {
            el.setAttribute('inputmode', 'numeric');
        }

        const regex = _FILTER_REGEX[rule];
        el.addEventListener('input', function () {
            const raw = el.value;
            const cleaned = raw.replace(regex, '');
            if (cleaned !== raw) {
                const pos = el.selectionStart;
                const diff = raw.length - cleaned.length;
                el.value = cleaned;
                if (pos !== null && typeof el.setSelectionRange === 'function') {
                    const nextPos = Math.max(0, pos - diff);
                    try { el.setSelectionRange(nextPos, nextPos); } catch (_) {}
                }
            }
        }, true);
    }

    function enhanceFilterBar(card) {
        if (!card || card.dataset.ctFilterEnhanced === '1') return;
        const form = card.querySelector('form') || card;
        const controls = Array.from(
            form.querySelectorAll('input[type="text"], input[type="search"], input[type="date"], input[type="number"], select')
        ).filter(function (el) {
            return !el.classList.contains('d-none') && (el.offsetParent !== null || Boolean(el.closest('.tab-pane')));
        });
        if (!controls.length) return;

        card.dataset.ctFilterEnhanced = '1';
        card.classList.add('ct-filter-enhanced');

        // Ocultar etiquetas legadas "FILTROS:" dentro de col-auto
        card.querySelectorAll('.col-auto').forEach(function (col) {
            if (col.querySelector('.bi-funnel, .bi-funnel-fill') && !col.querySelector('input, select, button, a')) {
                col.classList.add('ct-legacy-label');
            }
        });

        // 1. Envolver cada control con un ícono discreto, sin etiquetas que repitan el placeholder.
        controls.forEach(function (el) {
            if (el.closest('.ct-field-box')) return;
            const ig = el.closest('.input-group');
            if (ig) {
                ig.querySelectorAll('.input-group-text').forEach(function (addon) {
                    addon.classList.add('d-none');
                });
                ig.classList.remove('input-group', 'input-group-sm');
            }
            const meta = _inferFieldMeta(el);
            const wrap = document.createElement('div');
            wrap.className = 'ct-field-box';

            const ico = document.createElement('i');
            ico.className = 'bi ' + meta.icon + ' ct-field-icon';
            ico.setAttribute('aria-hidden', 'true');

            el.parentNode.insertBefore(wrap, el);
            wrap.appendChild(ico);
            wrap.appendChild(el);

            if (el.tagName === 'SELECT' && (el.name || el.id || '').toLowerCase().includes('estado')) {
                const statusDot = document.createElement('span');
                statusDot.className = 'ct-status-dot';
                statusDot.setAttribute('aria-hidden', 'true');
                wrap.appendChild(statusDot);
                el.classList.add('ct-status-select');

                const syncStatusStyle = function () {
                    Array.from(el.options).forEach(function (option) {
                        const optionTone = _inferDotClass(option.value, option.textContent).replace('ct-dot--', '');
                        if (optionTone) option.dataset.ctStatusTone = optionTone;
                    });

                    const selected = el.options[el.selectedIndex];
                    const toneClass = selected ? _inferDotClass(selected.value, selected.textContent) : '';
                    const tone = toneClass.replace('ct-dot--', '');
                    statusDot.className = 'ct-status-dot' + (tone ? ' ct-status-dot--' + tone : '');
                    el.classList.remove('ct-status-select--green', 'ct-status-select--blue', 'ct-status-select--amber', 'ct-status-select--red', 'ct-status-select--slate');
                    if (tone) el.classList.add('ct-status-select--' + tone);
                };

                el.addEventListener('change', syncStatusStyle);
                syncStatusStyle();
            }
            _attachInputSanitizer(el);
        });

        // 2. Mejorar botón limpiar filtros (enlaces o botones #clear-filters*)
        const clearBtn =
            card.querySelector('.filter-clear-btn') ||
            card.querySelector('button[id^="clear-filters"]') ||
            card.querySelector('a[title*="Limpiar"], a[aria-label*="Limpiar"], button[title*="Limpiar"]');
        if (clearBtn) {
            clearBtn.classList.add('ct-clear-btn');
            if (!clearBtn.textContent.trim() || clearBtn.textContent.trim().toLowerCase() === 'limpiar') {
                clearBtn.innerHTML = '<i class="bi bi-eraser"></i><span>Limpiar filtros</span>';
            }
            _updateClearBtnState(form, clearBtn);
            controls.forEach(function (el) {
                el.addEventListener('input', function () { _updateClearBtnState(form, clearBtn); });
                el.addEventListener('change', function () { _updateClearBtnState(form, clearBtn); });
            });
        }

        // 3. El filtro desplegable es la única fuente de selección de estado.
        if (card.previousElementSibling && card.previousElementSibling.classList.contains('ct-quick-filters')) {
            card.previousElementSibling.remove();
        }
    }

    function initAll(scope) {
        const root = scope || document;
        root.querySelectorAll('.ct-quick-filters').forEach(function (strip) { strip.remove(); });
        const forms = root.querySelectorAll(
            'form[data-ajax-filter-form="true"], form[data-tbody-id], form#filterForm, form.standard-filter-form, form.ajax-filter-form, .filter-bar-card form, .filter-card-container form'
        );
        forms.forEach(bindStandardAutoFilter);
        const cards = root.querySelectorAll('.filter-bar-card, .filter-card-container');
        cards.forEach(enhanceFilterBar);
    }

    if (global.AppPageLifecycle && typeof global.AppPageLifecycle.onPageLoad === 'function') {
        global.AppPageLifecycle.onPageLoad(function () { initAll(); });
    } else {
        document.addEventListener('DOMContentLoaded', function () { initAll(); });
    }

    global.AjaxFilters = { init: initAll, bind: bindStandardAutoFilter, enhance: enhanceFilterBar };
})(window);
