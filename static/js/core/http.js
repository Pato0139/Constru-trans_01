/**
 * http.js
 * Módulo HTTP helper para peticiones AJAX con soporte de CSRF,
 * debounce y manejo centralizado de errores.
 * @namespace AppHTTP
 */
window.AppHTTP = (() => {

    /**
     * Obtiene el valor de una cookie por nombre.
     * Usado internamente para leer el token CSRF de Django.
     * @param {string} name - Nombre de la cookie
     * @returns {string} Valor de la cookie o cadena vacía si no existe
     */
    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
        return '';
    }

    /**
     * Realiza una petición fetch y parsea la respuesta como JSON.
     * Agrega automáticamente el header X-Requested-With y el token CSRF
     * para peticiones que no sean GET.
     * @param {string} url - URL del endpoint
     * @param {Object} [options={}] - Opciones de la petición
     * @param {string} [options.method='GET'] - Método HTTP
     * @param {Object} [options.headers={}] - Headers adicionales
     * @param {BodyInit} [options.body] - Cuerpo de la petición
     * @returns {Promise<Object>} Datos JSON de la respuesta
     * @throws {Error} Si la respuesta no es JSON válido o el servidor devuelve error
     */
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

        if (options.body) config.body = options.body;

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

    /**
     * Crea una versión debounced de una función.
     * Útil para evitar llamadas excesivas en eventos como input o resize.
     * @param {Function} fn - Función a debounce
     * @param {number} [delay=300] - Milisegundos de espera
     * @returns {Function} Función debounced
     */
    function debounce(fn, delay = 300) {
        let timer = null;
        return (...args) => {
            clearTimeout(timer);
            timer = setTimeout(() => fn(...args), delay);
        };
    }

    /**
     * Muestra un mensaje de error al usuario.
     * Usa SweetAlert2 si está disponible, de lo contrario usa alert nativo.
     * @param {string} [message='Ocurrió un error'] - Mensaje a mostrar
     */
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

    return { fetchJSON, debounce, showError };
})();
