/**
 * HTTP helper module for AJAX requests with CSRF, debouncing, and error handling
 */
window.AppHTTP = (() => {
    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
        return '';
    }

    async function fetchJSON(url, options = {}) {
        const config = {
            method: options.method || 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                ...(options.headers || {})
            }
        };

        if (config.method !== 'GET' && !config.headers['X-CSRFToken']) {
            config.headers['X-CSRFToken'] = getCookie('csrftoken');
        }

        if (options.body) {
            config.body = options.body;
        }

        const response = await fetch(url, config);

        let data;
        try {
            data = await response.json();
        } catch {
            throw new Error('La respuesta no es JSON válido');
        }

        if (!response.ok) {
            throw new Error(data.error || data.message || 'Error de red');
        }

        return data;
    }

    function debounce(fn, delay = 300) {
        let timer = null;
        return (...args) => {
            clearTimeout(timer);
            timer = setTimeout(() => fn(...args), delay);
        };
    }

    function showError(message = 'Ocurrió un error') {
        if (window.Swal) {
            Swal.fire({
                icon: 'error',
                title: 'Error',
                text: message,
                background: '#161a22',
                color: '#fff'
            });
        } else {
            alert(message);
        }
    }

    return {
        fetchJSON,
        debounce,
        showError
    };
})();
