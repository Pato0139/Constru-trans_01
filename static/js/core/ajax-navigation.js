window.AppPageLifecycle = (() => {
    const pageLoadHandlers = new Map();
    let ready = document.readyState !== 'loading';
    let navigating = false;

    function runPageLoadHandlers() {
        pageLoadHandlers.forEach((once, handler) => {
            try {
                handler();
            } catch (error) {
                console.error('No se pudo inicializar una interacción de la página.', error);
            }
            if (once) pageLoadHandlers.delete(handler);
        });
    }

    document.addEventListener('DOMContentLoaded', () => {
        ready = true;
        runPageLoadHandlers();
    }, { once: true });

    document.addEventListener('app:page-loaded', () => {
        navigating = false;
        runPageLoadHandlers();
        if (window.AOS) window.AOS.refreshHard();
    });

    return {
        onPageLoad(handler, options = {}) {
            pageLoadHandlers.set(handler, options.once === true);
            if (ready && !navigating) runPageLoadHandlers();
        },
        beginNavigation() {
            navigating = true;
        },
        finishNavigation() {
            document.dispatchEvent(new Event('app:page-loaded'));
        }
    };
})();

window.AppAjaxNavigation = (() => {
    const contentSelector = '[data-ajax-content]';
    let loadedScripts = null;
    let activeRequest = null;
    let pageScopedListeners = [];

    document.head.querySelectorAll('style').forEach((style) => {
        style.dataset.ajaxNavigationStyle = 'true';
    });

    const progressStyle = document.createElement('style');
    progressStyle.textContent = `
        @keyframes app-ajax-progress-slide {
            from { transform: translateX(-110%); }
            to { transform: translateX(440%); }
        }
        #app-ajax-progress {
            position: fixed;
            inset: 0 auto auto 0;
            z-index: 2000;
            width: 24%;
            height: 3px;
            background: var(--color-accent, #f5b942);
            animation: app-ajax-progress-slide 1.2s ease-in-out infinite;
        }
    `;
    document.head.appendChild(progressStyle);

    function setNavigationPending(pending) {
        let progress = document.getElementById('app-ajax-progress');
        if (pending && !progress) {
            progress = document.createElement('div');
            progress.id = 'app-ajax-progress';
            progress.setAttribute('role', 'progressbar');
            progress.setAttribute('aria-label', 'Cargando página');
            document.body.appendChild(progress);
        }
        if (progress) progress.hidden = !pending;
        document.querySelector(contentSelector)?.toggleAttribute('aria-busy', pending);
    }

    function canNavigateTo(url) {
        return url.origin === window.location.origin &&
            url.protocol.startsWith('http') &&
            !/^\/(?:login|logout|registro|password-reset|reset)(?:\/|$)/i.test(url.pathname) &&
            !url.pathname.match(/\.(?:pdf|xlsx?|csv|xml|zip|docx?|png|jpe?g)$/i);
    }

    function hasFileInput(form) {
        return form.querySelector('input[type="file"]') !== null;
    }

    function synchronizeNavigationChrome(nextDocument) {
        const currentSidebar = document.querySelector('.sidebar-custom');
        const nextSidebar = nextDocument.querySelector('.sidebar-custom');
        if (!currentSidebar || !nextSidebar) return;

        currentSidebar.querySelectorAll('a.nav-link-premium[href]').forEach((link) => {
            const nextLink = Array.from(nextSidebar.querySelectorAll('a.nav-link-premium[href]'))
                .find((candidate) => candidate.href === link.href);
            link.classList.toggle('active', Boolean(nextLink?.classList.contains('active')));
        });

        currentSidebar.querySelectorAll('button[data-bs-target]').forEach((button) => {
            const nextButton = nextSidebar.querySelector(button.dataset.bsTarget);
            if (!nextButton) return;
            button.classList.toggle('collapsed', nextButton.classList.contains('collapsed'));
            button.setAttribute('aria-expanded', nextButton.getAttribute('aria-expanded') || 'false');

            const panel = document.querySelector(button.dataset.bsTarget);
            const nextPanel = nextSidebar.querySelector(button.dataset.bsTarget);
            if (panel && nextPanel) panel.classList.toggle('show', nextPanel.classList.contains('show'));
        });
    }

    function synchronizeMessages(nextDocument) {
        const currentMessages = document.getElementById('django-messages-data');
        const nextMessages = nextDocument.getElementById('django-messages-data');
        if (nextMessages) {
            const replacement = nextMessages.cloneNode(true);
            if (currentMessages) currentMessages.replaceWith(replacement);
            else document.querySelector(contentSelector)?.before(replacement);
        } else {
            currentMessages?.remove();
        }
    }

    function synchronizeStyles(nextDocument) {
        document.head.querySelectorAll('style[data-ajax-navigation-style]').forEach((style) => {
            style.remove();
        });
        nextDocument.head.querySelectorAll('style').forEach((style) => {
            const replacement = style.cloneNode(true);
            replacement.dataset.ajaxNavigationStyle = 'true';
            document.head.appendChild(replacement);
        });

        const currentStyles = new Map(
            Array.from(document.head.querySelectorAll('link[rel="stylesheet"][href]'))
                .map((link) => [link.href, link])
        );
        const nextStyles = new Set(
            Array.from(nextDocument.head.querySelectorAll('link[rel="stylesheet"][href]'))
                .map((link) => link.href)
        );

        currentStyles.forEach((link, href) => {
            if (!nextStyles.has(href)) link.remove();
        });

        nextDocument.head.querySelectorAll('link[rel="stylesheet"][href]').forEach((link) => {
            if (!currentStyles.has(link.href)) {
                document.head.appendChild(link.cloneNode(true));
            }
        });
    }

    function ensureLoadedScripts() {
        const scriptKey = (src) => {
            const url = new URL(src, window.location.href);
            return url.origin === window.location.origin ? url.pathname : url.href;
        };
        if (!loadedScripts) {
            loadedScripts = new Set(
                Array.from(document.scripts)
                    .map((script) => script.src)
                    .filter(Boolean)
                    .map(scriptKey)
            );
        }
        return scriptKey;
    }

    function pageScripts(nextDocument) {
        const scriptKey = ensureLoadedScripts();
        return Array.from(new Set(Array.from(nextDocument.scripts)
            .filter((script) => script.src)
            .map((script) => script.src)
            .filter((src) => !loadedScripts.has(scriptKey(src)))));
    }

    function registerInlineScript(src) {
        const url = new URL(src, window.location.href);
        loadedScripts.add(url.origin === window.location.origin ? url.pathname : url.href);
    }

    function runInlineScripts(nextDocument) {
        nextDocument.querySelectorAll('script:not([src])').forEach((source) => {
            if (source.hasAttribute('data-ajax-persistent')) return;
            const type = (source.type || 'text/javascript').toLowerCase();
            if (type !== 'text/javascript' && type !== 'application/javascript' && type !== 'module') return;

            const sourceText = source.textContent || '';
            if (!sourceText.trim()) return;

            const script = document.createElement('script');
            if (source.type) script.type = source.type;
            script.dataset.ajaxInlineScript = 'true';
            script.textContent = sourceText;

            const originalDocumentListener = document.addEventListener;
            const originalWindowListener = window.addEventListener;
            document.addEventListener = function (type, listener, options) {
                if ((type === 'DOMContentLoaded' || type === 'load') && typeof listener === 'function') {
                    return window.AppPageLifecycle.onPageLoad(
                        () => listener.call(document, new Event(type)),
                        { once: true }
                    );
                }
                pageScopedListeners.push([document, type, listener, options]);
                return originalDocumentListener.call(this, type, listener, options);
            };
            window.addEventListener = function (type, listener, options) {
                if ((type === 'DOMContentLoaded' || type === 'load') && typeof listener === 'function') {
                    return window.AppPageLifecycle.onPageLoad(
                        () => listener.call(window, new Event(type)),
                        { once: true }
                    );
                }
                pageScopedListeners.push([window, type, listener, options]);
                return originalWindowListener.call(this, type, listener, options);
            };

            try {
                document.body.appendChild(script);
            } finally {
                document.addEventListener = originalDocumentListener;
                window.addEventListener = originalWindowListener;
            }
        });
    }

    function loadScript(src) {
        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = src;
            script.onload = () => {
                registerInlineScript(src);
                resolve();
            };
            script.onerror = () => reject(new Error(`No se pudo cargar el script ${src}`));
            document.body.appendChild(script);
        });
    }

    async function renderResponse(response, requestedUrl, replaceHistory) {
        const html = await response.text();
        const nextDocument = new DOMParser().parseFromString(html, 'text/html');
        const currentContent = document.querySelector(contentSelector);
        const nextContent = nextDocument.querySelector(contentSelector);
        const currentShell = document.body.dataset.ajaxShell;
        const nextShell = nextDocument.body.dataset.ajaxShell;

        const isRenderableStatus = response.ok || response.status === 400 || response.status === 422;
        if (!isRenderableStatus || !currentContent || !nextContent || !currentShell || currentShell !== nextShell ||
            !canNavigateTo(new URL(response.url || requestedUrl.href, window.location.href))) {
            window.location.assign(response.url || requestedUrl.href);
            return false;
        }

        document.title = nextDocument.title;
        synchronizeStyles(nextDocument);
        synchronizeNavigationChrome(nextDocument);
        synchronizeMessages(nextDocument);
        pageScopedListeners.forEach(([target, type, listener, options]) => {
            target.removeEventListener(type, listener, options);
        });
        pageScopedListeners = [];
        if (window.jQuery && window.jQuery.fn.dataTable) {
            let dataTablesDestroyed = true;
            window.jQuery(currentContent).find('table').each(function () {
                if (window.jQuery.fn.dataTable.isDataTable(this)) {
                    try {
                        window.jQuery(this).DataTable().destroy();
                    } catch (error) {
                        console.error('No se pudo cerrar una tabla antes de la navegación AJAX.', error);
                        dataTablesDestroyed = false;
                        return false;
                    }
                }
            });
            if (!dataTablesDestroyed) {
                window.location.assign(response.url || requestedUrl.href);
                return false;
            }
        }
        if (typeof window.cleanupOrphanTooltips === 'function') {
            window.cleanupOrphanTooltips();
        } else {
            document.querySelectorAll('.tooltip').forEach((t) => t.remove());
        }
        window.AppPageLifecycle.beginNavigation();
        currentContent.replaceWith(nextContent);

        const destination = new URL(response.url || requestedUrl.href, window.location.href);
        if (replaceHistory) {
            window.history.replaceState({}, '', destination);
        } else {
            window.history.pushState({}, '', destination);
        }

        try {
            for (const src of pageScripts(nextDocument)) {
                await loadScript(src);
            }
            runInlineScripts(nextDocument);
        } catch (error) {
            AppHTTP.showError('No se pudieron cargar los componentes de esta página.');
            console.error(error);
        } finally {
            window.AppPageLifecycle.finishNavigation();
        }

        currentContent.removeAttribute('aria-busy');
        window.scrollTo({ top: 0, behavior: 'instant' });
        return true;
    }

    async function navigate(url, options = {}) {
        const destination = new URL(url, window.location.href);
        if (!canNavigateTo(destination)) {
            window.location.assign(destination.href);
            return;
        }

        ensureLoadedScripts();
        if (activeRequest) activeRequest.abort();
        activeRequest = new AbortController();
        const requestController = activeRequest;
        const headers = { 'X-App-Navigation': 'true' };
        const fetchOptions = {
            method: options.method || 'GET',
            headers,
            signal: requestController.signal,
            credentials: 'same-origin'
        };
        if (options.body) fetchOptions.body = options.body;

        setNavigationPending(true);
        let renderingResponse = false;
        try {
            const response = await fetch(destination.href, fetchOptions);
            if (requestController !== activeRequest) return;
            if (response.headers.get('content-disposition')?.includes('attachment')) {
                window.location.assign(response.url || destination.href);
                return;
            }
            const contentType = response.headers.get('content-type') || '';

            if (contentType.includes('application/json')) {
                const data = await response.json();
                if (!response.ok || data.status === 'error' || data.error) {
                    throw new Error(data.message || data.error || 'No se pudo completar la solicitud.');
                }
                if (data.message && window.Swal) {
                    Swal.fire({ icon: 'success', text: data.message, toast: true, position: 'top-end', timer: 3000, showConfirmButton: false });
                }
                await navigate(window.location.href, { replaceHistory: true });
                return;
            }

            renderingResponse = true;
            const rendered = await renderResponse(
                response,
                destination,
                options.replaceHistory || fetchOptions.method !== 'GET'
            );
            renderingResponse = false;
            if (!rendered) return;
        } catch (error) {
            if (error.name !== 'AbortError') {
                console.error(error);
                if (renderingResponse) {
                    window.location.assign(destination.href);
                    return;
                }
                AppHTTP.showError(error.message || 'No se pudo completar la solicitud.');
            }
        } finally {
            if (requestController === activeRequest) {
                activeRequest = null;
                setNavigationPending(false);
            }
        }
    }

    document.addEventListener('click', (event) => {
        if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
        const target = event.target instanceof Element ? event.target : null;
        const link = target?.closest('a[href]');
        if (!link || link.target || link.hasAttribute('download') || link.closest('[data-bs-toggle]') ||
            link.classList.contains('confirm-logout') || link.href.endsWith('#')) return;

        const destination = new URL(link.href, window.location.href);
        if (!canNavigateTo(destination) || destination.pathname === window.location.pathname &&
            destination.search === window.location.search && destination.hash) return;

        event.preventDefault();
        navigate(destination.href);
    });

    document.addEventListener('submit', (event) => {
        const form = event.target;
        if (!(form instanceof HTMLFormElement) || event.defaultPrevented ||
            !form.closest(contentSelector) || form.target || form.dataset.ajax === 'false' ||
            form.enctype === 'multipart/form-data' || hasFileInput(form)) return;

        const destination = new URL(form.action || window.location.href, window.location.href);
        if (!canNavigateTo(destination)) return;

        event.preventDefault();
        const method = (form.method || 'GET').toUpperCase();
        if (method === 'GET') {
            const params = new URLSearchParams(new FormData(form));
            destination.search = params.toString();
            navigate(destination.href);
            return;
        }

        const formData = event.submitter
            ? new FormData(form, event.submitter)
            : new FormData(form);
        navigate(destination.href, { method, body: formData });
    });

    window.addEventListener('popstate', () => {
        navigate(window.location.href, { replaceHistory: true });
    });

    return { navigate };
})();
