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
                const card = form.closest('.filter-bar-card');
                if (card && card.previousElementSibling && card.previousElementSibling.classList.contains('ct-quick-filters')) {
                    card.previousElementSibling.querySelectorAll('.ct-quick-chip').forEach(function (chip) {
                        chip.classList.toggle('is-active', chip.dataset.value === '');
                    });
                }
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
       - Agrega micro-etiquetas e íconos en cada campo
       - Genera chips de "Acceso rápido" con punto semántico para filtros de estado
       - Mejora el botón "Limpiar filtros" y soporta limpieza instantánea por AJAX
       ===================================================================== */
    function _inferFieldMeta(el) {
        const name = (el.getAttribute('name') || el.id || '').toLowerCase();
        const tag = el.tagName;
        const type = (el.getAttribute('type') || '').toLowerCase();
        const customLabel = (el.dataset.filterLabel || '').trim();
        const placeholder = (el.getAttribute('placeholder') || '').trim();
        const firstOpt = tag === 'SELECT' && el.options.length ? (el.options[0].textContent || '').trim() : '';

        let label = customLabel;
        if (!label) {
            if (type === 'date') {
                if (name.includes('inicio') || name.includes('desde')) label = 'Desde';
                else if (name.includes('fin') || name.includes('hasta')) label = 'Hasta';
                else label = 'Fecha';
            } else if (tag === 'SELECT') {
                if (name.includes('estado')) label = 'Estado';
                else if (name.includes('tipo')) label = 'Tipo';
                else if (name.includes('rol')) label = 'Rol';
                else if (name.includes('categoria')) label = 'Categoría';
                else if (name.includes('marca')) label = 'Marca';
                else if (name.includes('proveedor')) label = 'Proveedor';
                else if (name.includes('modulo')) label = 'Módulo';
                else if (name.includes('accion')) label = 'Acción';
                else if (name.includes('metodo')) label = 'Método';
                else if (firstOpt) label = firstOpt.replace(/\(.*?\)/g, '').replace(/^(todos|todas)\s*(los|las)?\s*/i, '').trim() || 'Filtro';
                else label = 'Filtro';
            } else {
                if (name === 'q' || name.includes('buscar') || name.includes('search')) label = 'Buscar';
                else if (name.includes('placa')) label = 'Placa';
                else if (name.includes('cliente')) label = 'Cliente';
                else if (name.includes('conductor')) label = 'Conductor';
                else if (name.includes('direccion') || name.includes('destino')) label = 'Destino';
                else if (name.includes('documento') || name.includes('nit')) label = 'Documento';
                else if (placeholder) label = placeholder.split(',')[0].replace(/\.\.\.$/, '').trim().slice(0, 18);
                else label = 'Buscar';
            }
        }

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

        return { label: label, icon: icon };
    }

    function _inferDotClass(value, text) {
        const s = ((value || '') + ' ' + (text || '')).toLowerCase();
        if (!value) return '';
        if (/(disponible|activo|activa|entregado|completado|aprobado|pagado|entrada|resuelt|cerrad|autorizado|verificado)/.test(s)) {
            return 'ct-dot--green';
        }
        if (/(ruta|camino|proceso|asignado|en_transito|transito|admin|conductor)/.test(s)) {
            return 'ct-dot--blue';
        }
        if (/(mantenimiento|pendiente|revision|revisión|correccion|corrección|abiert|espera|cliente|parcial)/.test(s)) {
            return 'ct-dot--amber';
        }
        if (/(inactivo|inactiva|cancelado|rechazado|suspendido|bloqueado|salida|bajo|agotado|incidente|fallid|vencid)/.test(s)) {
            return 'ct-dot--red';
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

        // 1. Envolver cada control con micro-etiqueta + ícono (incluyendo los que venían en .input-group)
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

            const lbl = document.createElement('span');
            lbl.className = 'ct-field-label';
            lbl.textContent = meta.label;

            const ico = document.createElement('i');
            ico.className = 'bi ' + meta.icon + ' ct-field-icon';
            ico.setAttribute('aria-hidden', 'true');

            el.parentNode.insertBefore(wrap, el);
            wrap.appendChild(lbl);
            wrap.appendChild(ico);
            wrap.appendChild(el);
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

        // 3. Crear barra "Acceso rápido" a partir del select principal (estado, tipo_movimiento, rol o el primer select disponible)
        const quickSelect =
            form.querySelector('select[name="estado"]') ||
            form.querySelector('select[name*="estado"]') ||
            form.querySelector('select[id*="estado"]') ||
            form.querySelector('select[name="tipo_movimiento"]') ||
            form.querySelector('select[name="rol"]') ||
            form.querySelector('select[id*="rol"]') ||
            form.querySelector('select');

        const disableQuickFilters = form.dataset.disableQuickFilters === 'true';
        if (disableQuickFilters && card.previousElementSibling && card.previousElementSibling.classList.contains('ct-quick-filters')) {
            card.previousElementSibling.remove();
        }

        if (!disableQuickFilters && quickSelect && quickSelect.options.length >= 2) {
            const parentContainer = card.parentNode;
            if (parentContainer && !(card.previousElementSibling && card.previousElementSibling.classList.contains('ct-quick-filters'))) {
                const strip = document.createElement('div');
                strip.className = 'ct-quick-filters';
                strip.setAttribute('role', 'group');
                strip.setAttribute('aria-label', 'Acceso rápido de filtros');

                const stripLabel = document.createElement('span');
                stripLabel.className = 'ct-quick-filters__label';
                stripLabel.textContent = 'Acceso rápido:';
                strip.appendChild(stripLabel);

                const chips = [];
                const allOpts = Array.from(quickSelect.options);
                // Mostrar "Todos" + hasta 6 opciones rápidas para mantener la barra limpia
                const visibleOpts = allOpts.slice(0, 7);
                if (quickSelect.value && !visibleOpts.some(function (o) { return o.value === quickSelect.value; })) {
                    const selectedOpt = allOpts.find(function (o) { return o.value === quickSelect.value; });
                    if (selectedOpt) visibleOpts.push(selectedOpt);
                }

                visibleOpts.forEach(function (opt) {
                    const btn = document.createElement('button');
                    btn.type = 'button';
                    btn.className = 'ct-quick-chip';
                    btn.dataset.value = opt.value;

                    const dotClass = _inferDotClass(opt.value, opt.textContent);
                    const cleanText = !opt.value ? 'Todos' : opt.textContent.trim();

                    if (dotClass) {
                        const dot = document.createElement('span');
                        dot.className = 'ct-dot ' + dotClass;
                        dot.setAttribute('aria-hidden', 'true');
                        btn.appendChild(dot);
                    }
                    const span = document.createElement('span');
                    span.textContent = cleanText;
                    btn.appendChild(span);

                    if (quickSelect.value === opt.value) {
                        btn.classList.add('is-active');
                    }

                    btn.addEventListener('click', function () {
                        if (quickSelect.value === opt.value) return;
                        quickSelect.value = opt.value;
                        chips.forEach(function (c) {
                            c.classList.toggle('is-active', c.dataset.value === quickSelect.value);
                        });
                        quickSelect.dispatchEvent(new Event('change', { bubbles: true }));
                    });

                    chips.push(btn);
                    strip.appendChild(btn);
                });

                quickSelect.addEventListener('change', function () {
                    chips.forEach(function (c) {
                        c.classList.toggle('is-active', c.dataset.value === quickSelect.value);
                    });
                });

                parentContainer.insertBefore(strip, card);
            }
        }
    }

    function initAll(scope) {
        const root = scope || document;
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
