(function (global) {
    function isAjaxRequest(form) {
        const ajaxFlag = form.dataset.ajaxFilterForm;
        if (ajaxFlag === 'true' || ajaxFlag === '1') return true;
        const tbodyId = form.dataset.tbodyId;
        return tbodyId && document.getElementById(tbodyId);
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
        form.dataset.autoBindDone = '1';

        const useAjax = isAjaxRequest(form);
        const tbodyId = form.dataset.tbodyId;
        const tbody = tbodyId ? document.getElementById(tbodyId) : null;
        const DEBOUNCE_MS = 350;

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
            if (global.bootstrap && typeof global.bootstrap.Tooltip !== 'undefined') {
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
                    tbody.innerHTML = html;
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

        global.addEventListener('popstate', function () {
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

    function initAll(scope) {
        const root = scope || document;
        const forms = root.querySelectorAll('form[data-ajax-filter-form="true"], form[data-tbody-id], form#filterForm, form.standard-filter-form, form.ajax-filter-form');
        forms.forEach(bindStandardAutoFilter);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () { initAll(); });
    } else {
        initAll();
    }

    global.AjaxFilters = { init: initAll, bind: bindStandardAutoFilter };
})(window);
