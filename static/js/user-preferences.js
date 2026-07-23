/**
 * Módulo de preferencias de usuario para temas, filtros de daltonismo, tamaño de fuente e idioma
 * @namespace UserPreferences
 */
(function () {
    'use strict';

    /**
     * Claves de localStorage para las preferencias
     * @constant {Object}
     * @property {string} theme - Tema visual
     * @property {string} daltonism - Filtro de daltonismo
     * @property {string} fontSize - Tamaño de fuente
     * @property {string} language - Idioma
     */
    var KEYS = {
        theme: 'theme',
        daltonism: 'daltonism',
        fontSize: 'fontSize',
        language: 'language',
    };

    /**
     * Valores predeterminados para las preferencias
     * @constant {Object}
     */
    var DEFAULTS = {
        theme: 'light',
        daltonism: 'none',
        fontSize: 'normal',
        language: 'es',
    };

    /**
     * Diccionarios de traducción para español e inglés
     * @constant {Object}
     */
    var I18N = {
        es: {
            'nav.panel': 'Panel de Control',
            'nav.welcome': 'Bienvenido de nuevo, ¡qué bueno verte!',
            'nav.accessibility': 'Accesibilidad',
            'nav.themes': 'TEMAS VISUALES',
            'nav.theme.dark': 'Modo Oscuro',
            'nav.theme.light': 'Modo Claro',
            'nav.theme.a11y': 'Alto Contraste',
            'nav.daltonism': 'MODOS PARA DALTONISMO',
            'nav.daltonism.none': 'Normal',
            'nav.daltonism.protanopia': 'Protanopia (Rojo)',
            'nav.daltonism.deuteranopia': 'Deuteranopia (Verde)',
            'nav.daltonism.tritanopia': 'Tritanopia (Azul)',
            'nav.daltonism.achromatopsia': 'Achromatopsia (Gris)',
            'nav.notifications': 'Notificaciones',
            'nav.notif.empty': 'No tienes notificaciones',
            'nav.notif.emptyHint': 'Las nuevas notificaciones aparecerán aquí',
            'nav.notif.viewAll': 'Ver todas las notificaciones',
            'settings.title': 'Configuraciones Avanzadas',
            'settings.font': 'Tamaño de Fuente',
            'settings.font.small': 'Pequeña',
            'settings.font.normal': 'Normal',
            'settings.font.large': 'Grande',
            'settings.font.xlarge': 'Extra Grande',
            'settings.lang': 'Idioma',
            'settings.lang.es': 'Español',
            'settings.lang.en': 'English',
            'settings.theme': 'Tema Visual',
            'settings.theme.dark': 'Oscuro',
            'settings.theme.light': 'Claro',
            'settings.theme.a11y': 'Alto Contraste',
            'settings.daltonism': 'Filtros para Daltonismo',
            'settings.daltonism.none': 'Normal',
            'settings.profile': 'Información de Perfil',
            'settings.profile.name': 'Nombre',
            'settings.profile.role': 'Rol',
            'settings.profile.doc': 'Documento',
            'settings.profile.edit': 'Editar Perfil',
            'toast.fontSize': 'Tamaño de fuente actualizado',
            'toast.theme': 'Tema visual actualizado',
            'toast.daltonism': 'Filtro de daltonismo aplicado',
            'toast.language': 'Idioma actualizado',
            'sidebar.brandSub': 'Panel de gestión',
            'sidebar.label.principal': 'Principal',
            'sidebar.general': 'General',
            'sidebar.label.operaciones': 'Operaciones',
            'sidebar.ventasCobros': 'Ventas y Cobros',
            'sidebar.gestionPedidos': 'Gestión Pedidos',
            'sidebar.pedidosAntiguos': 'Pedidos Antiguos',
            'sidebar.facturacion': 'Facturación',
            'sidebar.pagos': 'Pagos',
            'sidebar.inventarioFlota': 'Inventario y Flota',
            'sidebar.materiales': 'Materiales',
            'sidebar.tiposMaterial': 'Tipos de Material',
            'sidebar.stock': 'Stock',
            'sidebar.movimientos': 'Movimientos',
            'sidebar.vehiculos': 'Vehículos',
            'sidebar.compras': 'Compras',
            'sidebar.proveedores': 'Proveedores',
            'sidebar.comprasList': 'Compras',
            'sidebar.entregas': 'Entregas',
            'sidebar.entregasList': 'Entregas',
            'sidebar.label.sistema': 'Sistema',
            'sidebar.administracion': 'Administración',
            'sidebar.gestionUsuarios': 'Gestión Usuarios',
            'sidebar.reportes': 'Reportes',
            'sidebar.auditoria': 'Auditoría',
            'sidebar.label.miCuenta': 'Mi cuenta',
            'sidebar.panelControl': 'Panel de Control',
            'sidebar.solicitarPedido': 'Solicitar Pedido',
            'sidebar.label.pedidos': 'Pedidos',
            'sidebar.misPedidos': 'Mis Pedidos',
            'sidebar.seguimiento': 'Seguimiento',
            'sidebar.historial': 'Historial',
            'sidebar.misFacturas': 'Mis Facturas',
            'sidebar.label.conductor': 'Conductor',
            'sidebar.panelConductor': 'Panel Conductor',
            'sidebar.misEntregas': 'Mis Entregas',
            'sidebar.label.configuracion': 'Configuración',
            'sidebar.miCuenta': 'Mi Cuenta',
            'sidebar.cerrarSesion': 'Cerrar Sesión',
        },
        en: {
            'nav.panel': 'Control Panel',
            'nav.welcome': 'Welcome back, good to see you!',
            'nav.accessibility': 'Accessibility',
            'nav.themes': 'VISUAL THEMES',
            'nav.theme.dark': 'Dark Mode',
            'nav.theme.light': 'Light Mode',
            'nav.theme.a11y': 'High Contrast',
            'nav.daltonism': 'COLOR BLIND MODES',
            'nav.daltonism.none': 'Normal',
            'nav.daltonism.protanopia': 'Protanopia (Red)',
            'nav.daltonism.deuteranopia': 'Deuteranopia (Green)',
            'nav.daltonism.tritanopia': 'Tritanopia (Blue)',
            'nav.daltonism.achromatopsia': 'Achromatopsia (Gray)',
            'nav.notifications': 'Notifications',
            'nav.notif.empty': 'You have no notifications',
            'nav.notif.emptyHint': 'New notifications will appear here',
            'nav.notif.viewAll': 'View all notifications',
            'settings.title': 'Advanced Settings',
            'settings.font': 'Font Size',
            'settings.font.small': 'Small',
            'settings.font.normal': 'Normal',
            'settings.font.large': 'Large',
            'settings.font.xlarge': 'Extra Large',
            'settings.lang': 'Language',
            'settings.lang.es': 'Spanish',
            'settings.lang.en': 'English',
            'settings.theme': 'Visual Theme',
            'settings.theme.dark': 'Dark',
            'settings.theme.light': 'Light',
            'settings.theme.a11y': 'High Contrast',
            'settings.daltonism': 'Color Blind Filters',
            'settings.daltonism.none': 'Normal',
            'settings.profile': 'Profile Information',
            'settings.profile.name': 'Name',
            'settings.profile.role': 'Role',
            'settings.profile.doc': 'ID Document',
            'settings.profile.edit': 'Edit Profile',
            'toast.fontSize': 'Font size updated',
            'toast.theme': 'Visual theme updated',
            'toast.daltonism': 'Color blind filter applied',
            'toast.language': 'Language updated',
            'sidebar.brandSub': 'Management panel',
            'sidebar.label.principal': 'Main',
            'sidebar.general': 'General',
            'sidebar.label.operaciones': 'Operations',
            'sidebar.ventasCobros': 'Sales and Collections',
            'sidebar.gestionPedidos': 'Order Management',
            'sidebar.pedidosAntiguos': 'Old Orders',
            'sidebar.facturacion': 'Invoicing',
            'sidebar.pagos': 'Payments',
            'sidebar.inventarioFlota': 'Inventory and Fleet',
            'sidebar.materiales': 'Materials',
            'sidebar.tiposMaterial': 'Material Types',
            'sidebar.stock': 'Stock',
            'sidebar.movimientos': 'Movements',
            'sidebar.vehiculos': 'Vehicles',
            'sidebar.compras': 'Purchases',
            'sidebar.proveedores': 'Suppliers',
            'sidebar.comprasList': 'Purchases',
            'sidebar.entregas': 'Deliveries',
            'sidebar.entregasList': 'Deliveries',
            'sidebar.label.sistema': 'System',
            'sidebar.administracion': 'Administration',
            'sidebar.gestionUsuarios': 'User Management',
            'sidebar.reportes': 'Reports',
            'sidebar.auditoria': 'Audit',
            'sidebar.label.miCuenta': 'My account',
            'sidebar.panelControl': 'Control Panel',
            'sidebar.solicitarPedido': 'Request Order',
            'sidebar.label.pedidos': 'Orders',
            'sidebar.misPedidos': 'My Orders',
            'sidebar.seguimiento': 'Tracking',
            'sidebar.historial': 'History',
            'sidebar.misFacturas': 'My Invoices',
            'sidebar.label.conductor': 'Driver',
            'sidebar.panelConductor': 'Driver Panel',
            'sidebar.misEntregas': 'My Deliveries',
            'sidebar.label.configuracion': 'Settings',
            'sidebar.miCuenta': 'My Account',
            'sidebar.cerrarSesion': 'Log Out',
        },
    };

    /**
     * Obtiene una preferencia del usuario de localStorage
     * @param {string} key - Clave de la preferencia
     * @returns {string} Valor de la preferencia o el predeterminado
     */
    function getPref(key) {
        var val = localStorage.getItem(KEYS[key]);
        return val !== null && val !== '' ? val : DEFAULTS[key];
    }

    /**
     * Establece una preferencia del usuario en localStorage
     * @param {string} key - Clave de la preferencia
     * @param {string} value - Valor a guardar
     */
    function setPref(key, value) {
        localStorage.setItem(KEYS[key], value);
    }

    /**
     * Restablece completamente todos los estilos en línea del body
     */
    function resetAllBodyStyles() {
        if (document.body) {
            document.body.style.backgroundColor = '';
            document.body.style.color = '';
            document.body.style.fontWeight = '';
            document.body.style.fontFamily = '';
        }
        // Also clear html element styles if any
        if (document.documentElement) {
            document.documentElement.style.filter = '';
        }
    }

    /**
     * Aplica el idioma seleccionado a la interfaz
     * @param {string} lang - Código de idioma ('es' o 'en')
     * @param {Object} [options] - Opciones adicionales
     * @param {boolean} [options.silent=false] - Si es true, no muestra toast
     */
    function applyLanguage(lang, options) {
        options = options || {};
        var dict = I18N[lang] || I18N.es;
        document.documentElement.lang = lang === 'en' ? 'en' : 'es';
        document.querySelectorAll('[data-i18n]').forEach(function (el) {
            var key = el.getAttribute('data-i18n');
            if (dict[key]) {
                if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
                    el.placeholder = dict[key];
                } else {
                    el.textContent = dict[key];
                }
            }
        });
        if (!options.silent) {
            showPreferenceToast('toast.language');
        }
    }

    /**
     * Aplica todas las preferencias guardadas
     */
    function applyAll() {
        var html = document.documentElement;
        var theme = getPref('theme');
        resetAllBodyStyles();
        
        html.setAttribute('data-theme', theme);
        html.setAttribute('data-daltonism', getPref('daltonism'));
        html.setAttribute('data-font-size', getPref('fontSize'));
        
        applyLanguage(getPref('language'), { silent: true });
    }

    /**
     * Muestra un toast notificando el cambio de preferencia
     * @param {string} messageKey - Clave del mensaje en el diccionario
     */
    function showPreferenceToast(messageKey) {
        if (typeof Swal === 'undefined') {
            return;
        }
        var lang = getPref('language');
        var dict = I18N[lang] || I18N.es;
        var text = dict[messageKey] || messageKey;
        var isDark = getPref('theme') !== 'light';
        Swal.fire({
            icon: 'success',
            title: lang === 'en' ? 'Done!' : '¡Listo!',
            text: text,
            toast: true,
            position: 'top-end',
            showConfirmButton: false,
            timer: 2000,
            background: isDark ? '#1a1a1a' : '#ffffff',
            color: isDark ? '#ffffff' : '#0f172a',
        });
    }

    /**
     * Sincroniza el estado visual de los botones de configuración
     */
    function syncSettingsButtons() {
        var theme = getPref('theme');
        var daltonism = getPref('daltonism');
        var fontSize = getPref('fontSize');
        var language = getPref('language');

        document.querySelectorAll('.theme-btn').forEach(function (btn) {
            btn.classList.toggle('active', btn.dataset.theme === theme);
        });
        document.querySelectorAll('.theme-option').forEach(function (item) {
            item.classList.toggle('active', item.dataset.themeValue === theme);
            item.setAttribute('aria-current', item.dataset.themeValue === theme ? 'true' : 'false');
        });
        document.querySelectorAll('.daltonism-btn').forEach(function (btn) {
            btn.classList.toggle('active', btn.dataset.daltonism === daltonism);
        });
        document.querySelectorAll('.daltonism-option').forEach(function (item) {
            item.classList.toggle('active', item.dataset.daltonismValue === daltonism);
            item.setAttribute('aria-current', item.dataset.daltonismValue === daltonism ? 'true' : 'false');
        });
        document.querySelectorAll('.font-size-btn').forEach(function (btn) {
            btn.classList.toggle('active', btn.dataset.size === fontSize);
        });
        document.querySelectorAll('.language-btn').forEach(function (btn) {
            btn.classList.toggle('active', btn.dataset.lang === language);
        });
    }

    /**
     * Establece el tema visual del usuario
     * @param {('dark'|'light'|'accessibility')} theme - Tema a aplicar
     * @returns {boolean} Siempre false para prevenir comportamiento por defecto
     */
    window.setTheme = function (theme) {
        var valid = ['dark', 'light', 'accessibility'];
        if (valid.indexOf(theme) === -1) {
            return false;
        }
        var html = document.documentElement;
        
        resetAllBodyStyles();
        html.setAttribute('data-theme', theme);
        setPref('theme', theme);
        
        syncSettingsButtons();
        showPreferenceToast('toast.theme');
        return false;
    };

    /**
     * Establece el filtro de daltonismo
     * @param {('none'|'protanopia'|'deuteranopia'|'tritanopia'|'achromatopsia')} mode - Modo de daltonismo
     * @returns {boolean} Siempre false para prevenir comportamiento por defecto
     */
    window.setDaltonism = function (mode) {
        var valid = ['none', 'protanopia', 'deuteranopia', 'tritanopia', 'achromatopsia'];
        if (valid.indexOf(mode) === -1) {
            return false;
        }
        var html = document.documentElement;
        html.style.filter = '';
        html.setAttribute('data-daltonism', mode);
        setPref('daltonism', mode);
        syncSettingsButtons();
        showPreferenceToast('toast.daltonism');
        return false;
    };

    /**
     * Establece el tamaño de fuente
     * @param {('small'|'normal'|'large'|'xlarge')} size - Tamaño de fuente
     * @returns {boolean} Siempre false para prevenir comportamiento por defecto
     */
    window.setFontSize = function (size) {
        var valid = ['small', 'normal', 'large', 'xlarge'];
        if (valid.indexOf(size) === -1) {
            return false;
        }
        document.documentElement.setAttribute('data-font-size', size);
        setPref('fontSize', size);
        syncSettingsButtons();
        showPreferenceToast('toast.fontSize');
        return false;
    };

    /**
     * Establece el idioma de la interfaz
     * @param {('es'|'en')} lang - Código de idioma
     * @returns {boolean} Siempre false para prevenir comportamiento por defecto
     */
    window.setLanguage = function (lang) {
        if (lang !== 'es' && lang !== 'en') {
            return false;
        }
        setPref('language', lang);
        applyLanguage(lang, { silent: true });
        syncSettingsButtons();
        showPreferenceToast('toast.language');
        return false;
    };

    window.syncSettingsButtons = syncSettingsButtons;
    window.getUserPreference = getPref;

    /**
     * Inicializa los listeners de eventos para la página de configuración
     */
    function initSettingsPage() {
        document.querySelectorAll('.font-size-btn').forEach(function (btn) {
            btn.addEventListener('click', function (e) {
                e.preventDefault();
                setFontSize(btn.dataset.size);
            });
        });
        document.querySelectorAll('.language-btn').forEach(function (btn) {
            btn.addEventListener('click', function (e) {
                e.preventDefault();
                setLanguage(btn.dataset.lang);
            });
        });
        document.querySelectorAll('.theme-btn').forEach(function (btn) {
            btn.addEventListener('click', function (e) {
                e.preventDefault();
                setTheme(btn.dataset.theme);
            });
        });
        document.querySelectorAll('.daltonism-btn').forEach(function (btn) {
            btn.addEventListener('click', function (e) {
                e.preventDefault();
                setDaltonism(btn.dataset.daltonism);
            });
        });
        syncSettingsButtons();
    }

    applyAll();

    /**
     * Inicializa el módulo cuando el DOM esté listo
     */
    document.addEventListener('DOMContentLoaded', function () {
        applyLanguage(getPref('language'), { silent: true });
        initSettingsPage();
        syncSettingsButtons();
    });
})();
