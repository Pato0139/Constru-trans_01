/**
 * base.js
 * Módulo principal de la aplicación: inicializa AOS, DataTables, sidebar,
 * validaciones de inputs globales y confirmaciones con SweetAlert2.
 */

// Inicializar Animate On Scroll
AOS.init({ duration: 800, once: true, easing: 'ease-in-out' });

/* =====================================================================
   Sidebar
   ===================================================================== */
const sidebarToggle  = document.getElementById('sidebarToggle');
const sidebarClose   = document.getElementById('sidebarClose');
const sidebar        = document.getElementById('sidebar');
const sidebarOverlay = document.getElementById('sidebarOverlay');

/** Abre el sidebar y bloquea el scroll del body */
function openSidebar() {
    if (!sidebar || !sidebarOverlay) return;
    sidebar.classList.add('active');
    sidebarOverlay.classList.add('active');
    document.body.style.overflow = 'hidden';
}

function closeSidebar() {
    if (!sidebar || !sidebarOverlay) return;
    sidebar.classList.remove('active');
    sidebarOverlay.classList.remove('active');
    document.body.style.overflow = '';
}

if (sidebarToggle) {
    sidebarToggle.addEventListener('click', () => {
        const isOpen = sidebar && sidebar.classList.contains('active');
        if (isOpen) {
            closeSidebar();
            return;
        }
        openSidebar();
    });
}

/** Cierra el sidebar desde el botón interno */
if (sidebarClose) {
    sidebarClose.addEventListener('click', closeSidebar);
}

/** Cierra el sidebar al hacer clic en el overlay */
if (sidebarOverlay) {
    sidebarOverlay.addEventListener('click', closeSidebar);
}

/** Cierra el sidebar automáticamente cuando el usuario selecciona una opción del menú móvil */
document.addEventListener('click', (event) => {
    const target = event.target.closest('#sidebar a');
    if (!target || !sidebar || !sidebarOverlay) return;

    const isMobileSidebar = window.innerWidth < 992;
    if (!isMobileSidebar) return;

    closeSidebar();
});

// Redirigir errores de DataTables a la consola en vez de ventanas emergentes
$.fn.dataTable.ext.errMode = 'throw';

/* =====================================================================
   DataTables
   ===================================================================== */
window.AppPageLifecycle.onPageLoad(function() {
    /**
     * Inicializa DataTables en todas las tablas que no tengan la clase .no-datatable
     */
    $('.table:not(.no-datatable)').each(function() {
        if ($.fn.dataTable.isDataTable(this)) return;
        $(this).DataTable({
        language: {
            search:        'Buscar:',
            lengthMenu:    'Mostrar _MENU_ registros por página',
            zeroRecords:   'No se encontraron resultados',
            info:          'Mostrando registros del _START_ al _END_ de un total de _TOTAL_ registros',
            infoEmpty:     'No hay registros disponibles',
            infoFiltered:  '(filtrado de _MAX_ registros totales)',
            paginate: {
                first:    'Primero',
                last:     'Último',
                next:     'Siguiente',
                previous: 'Anterior'
            }
        },
        pageLength: 10,
        responsive: true,
        dom: '<"d-flex justify-content-between align-items-center flex-wrap gap-3 mb-3"l>rt<"d-flex justify-content-between align-items-center flex-wrap gap-3 mt-4"ip>'
        });
    });

    /**
     * Muestra mensajes de Django usando SweetAlert2 toast
     * Los mensajes se inyectan desde el div #django-messages-data
     */
    const djangoMessagesDiv = document.getElementById('django-messages-data');
    if (djangoMessagesDiv && djangoMessagesDiv.dataset.toastShown !== 'true') {
        djangoMessagesDiv.dataset.toastShown = 'true';
        const isLight = (document.documentElement.getAttribute('data-theme') || document.body.getAttribute('data-theme')) === 'light';
        djangoMessagesDiv.querySelectorAll('.django-message-item').forEach(msgEl => {
            const tags = (msgEl.dataset.tags || '').toLowerCase();
            const text = (msgEl.dataset.text || '').trim();
            if (!text) return;

            let icon = 'info';
            let title = 'Información';
            let iconColor = '#3b82f6';
            if (tags.includes('error') || tags.includes('danger')) {
                icon = 'error';
                title = 'Error';
                iconColor = '#ef4444';
            } else if (tags.includes('warning')) {
                icon = 'warning';
                title = 'Atención';
                iconColor = '#f59e0b';
            } else if (tags.includes('success')) {
                icon = 'success';
                title = '¡Listo!';
                iconColor = '#10b981';
            }

            Swal.fire({
                icon,
                title,
                text,
                toast: true,
                position: 'top-end',
                showConfirmButton: false,
                showCloseButton: true,
                timer: 4500,
                timerProgressBar: true,
                background: isLight ? '#ffffff' : '#1e293b',
                color: isLight ? '#0f172a' : '#f8fafc',
                iconColor,
                didOpen: (toast) => {
                    toast.onmouseenter = Swal.stopTimer;
                    toast.onmouseleave = Swal.resumeTimer;
                },
                customClass: { popup: 'rounded-4 shadow-lg' }
            });
        });
    }
});

/* =====================================================================
   Validación de inputs globales
   ===================================================================== */

/**
 * Permite solo dígitos en inputs con clase .numeric-only
 */
$(document).on('input', '.numeric-only', function() {
    this.value = this.value.replace(/[^0-9]/g, '');
});

/**
 * Permite solo números decimales (punto o coma) en inputs con clase .decimal-only
 * Limita a 2 decimales
 */
$(document).on('input', '.decimal-only', function() {
    let value = this.value.replace(/[^0-9\.,]/g, '').replace(/,/g, '.');
    const parts = value.split('.');
    if (parts.length > 2) value = parts.shift() + '.' + parts.join('');
    if (value.includes('.')) {
        const [intPart, decPart] = value.split('.');
        value = intPart + '.' + decPart.slice(0, 2);
    }
    this.value = value;
});

/**
 * Permite solo caracteres alfanuméricos en inputs con clase .alphanumeric-only
 */
$(document).on('input', '.alphanumeric-only', function() {
    this.value = this.value.replace(/[^a-zA-Z0-9]/g, '');
});

/**
 * Permite solo caracteres válidos para placas vehiculares (mayúsculas + dígitos)
 * en inputs con clase .plate-only
 */
$(document).on('input', '.plate-only', function() {
    this.value = this.value.toUpperCase().replace(/[^A-Z0-9]/g, '');
});

/**
 * Protección global contra números negativos, notación científica (e/E) y ceros inválidos
 * en todos los inputs numéricos de precios, cantidades, stock y capacidades.
 */
$(document).on('keydown', 'input[type="number"]', function(e) {
    const minAttr = this.getAttribute('min');
    const minVal = minAttr !== null && minAttr !== '' ? parseFloat(minAttr) : 0;
    const allowNegative = !Number.isNaN(minVal) && minVal < 0;
    const blocked = allowNegative ? ['e', 'E', '+'] : ['-', 'e', 'E', '+'];
    if (blocked.includes(e.key)) {
        e.preventDefault();
    }
});

$(document).on('input change blur', 'input[type="number"]', function(e) {
    const minAttr = this.getAttribute('min');
    const minVal = minAttr !== null && minAttr !== '' ? parseFloat(minAttr) : 0;
    const maxAttr = this.getAttribute('max');
    const maxVal = maxAttr !== null && maxAttr !== '' ? parseFloat(maxAttr) : null;
    const allowNegative = !Number.isNaN(minVal) && minVal < 0;

    if (!allowNegative && typeof this.value === 'string' && this.value.includes('-')) {
        this.value = this.value.replace(/-/g, '');
    }

    if (e.type === 'change' || e.type === 'blur') {
        if (this.value === '') return;
        const num = parseFloat(this.value);
        if (Number.isNaN(num)) {
            this.value = !Number.isNaN(minVal) ? String(minVal) : '';
            return;
        }
        if (!Number.isNaN(minVal) && num < minVal) {
            this.value = String(minVal);
        } else if (maxVal !== null && !Number.isNaN(maxVal) && num > maxVal) {
            this.value = String(maxVal);
        }
    }
});

/* =====================================================================
   Confirmaciones y Alertas SweetAlert2 (Continuar / Cancelar)
   ===================================================================== */

function _swalThemeColors() {
    const isLight = (document.documentElement.getAttribute('data-theme') || document.body.getAttribute('data-theme')) === 'light';
    return {
        isLight,
        background: isLight ? '#ffffff' : '#1e293b',
        color: isLight ? '#0f172a' : '#f8fafc',
        cancelButtonColor: isLight ? '#64748b' : '#475569',
    };
}

window.AppAlert = function(message, title = 'Validación', icon = 'warning') {
    if (typeof Swal === 'undefined') {
        window.alert(message);
        return Promise.resolve();
    }
    const theme = _swalThemeColors();
    return Swal.fire({
        title,
        text: message,
        icon,
        confirmButtonText: 'Entendido',
        confirmButtonColor: '#2563eb',
        background: theme.background,
        color: theme.color,
        customClass: { popup: 'rounded-4 border-white-10 shadow-2xl' }
    });
};

window.AppConfirm = function(options = {}) {
    const {
        title = '¿Deseas continuar?',
        text = 'Confirma esta acción para continuar.',
        icon = 'question',
        confirmText = 'Continuar',
        cancelText = 'Cancelar',
        confirmColor = '#2563eb',
    } = options;
    if (typeof Swal === 'undefined') {
        return Promise.resolve({ isConfirmed: window.confirm(text || title) });
    }
    const theme = _swalThemeColors();
    return Swal.fire({
        title,
        text,
        icon,
        showCancelButton: true,
        confirmButtonColor: confirmColor,
        cancelButtonColor: theme.cancelButtonColor,
        confirmButtonText: confirmText,
        cancelButtonText: cancelText,
        background: theme.background,
        color: theme.color,
        customClass: { popup: 'rounded-4 border-white-10 shadow-2xl' }
    });
};

/**
 * Confirmación universal con SweetAlert2 (Continuar / Cancelar) para cualquier
 * formulario o botón con data-confirm-action="Mensaje".
 */
$(document).on('submit', 'form[data-confirm-action]', function(e) {
    const form = this;
    if (form.dataset.confirmApproved === '1') {
        delete form.dataset.confirmApproved;
        return;
    }
    e.preventDefault();
    const title = form.dataset.confirmTitle || 'Confirmar acción';
    const text = form.dataset.confirmAction || '¿Deseas continuar con esta acción?';
    const confirmText = form.dataset.confirmBtn || 'Continuar';
    const confirmColor = form.dataset.confirmColor || '#2563eb';
    const icon = form.dataset.confirmIcon || 'question';

    window.AppConfirm({ title, text, icon, confirmText, cancelText: 'Cancelar', confirmColor })
        .then(result => {
            if (result.isConfirmed) {
                form.dataset.confirmApproved = '1';
                form.requestSubmit();
            }
        });
});

$(document).on('click', 'button[data-confirm-action], a[data-confirm-action]', function(e) {
    const el = this;
    if (el.dataset.confirmApproved === '1') {
        delete el.dataset.confirmApproved;
        return;
    }
    e.preventDefault();
    const title = el.dataset.confirmTitle || 'Confirmar acción';
    const text = el.dataset.confirmAction || '¿Deseas continuar con esta acción?';
    const confirmText = el.dataset.confirmBtn || 'Continuar';
    const confirmColor = el.dataset.confirmColor || '#2563eb';
    const icon = el.dataset.confirmIcon || 'question';

    window.AppConfirm({ title, text, icon, confirmText, cancelText: 'Cancelar', confirmColor })
        .then(result => {
            if (!result.isConfirmed) return;
            if (el.tagName === 'A' && el.href) {
                window.location.href = el.href;
            } else {
                const form = el.closest('form');
                if (form) {
                    el.dataset.confirmApproved = '1';
                    form.requestSubmit(el);
                }
            }
        });
});

/**
 * Confirmación de cierre de sesión para elementos con clase .confirm-logout
 * @param {Event} e - Evento click
 */
$(document).on('click', '.confirm-logout', function(e) {
    e.preventDefault();
    const url = $(this).attr('href');
    window.AppConfirm({
        title: '¿Cerrar sesión?',
        text: '¿Estás seguro de que deseas salir del sistema?',
        icon: 'question',
        confirmText: 'Continuar y salir',
        cancelText: 'Cancelar',
        confirmColor: '#f97316',
    }).then(result => { if (result.isConfirmed) window.location.href = url; });
});

/**
 * Confirmación para formularios con clase .confirm-delete-form
 */
$(document).on('click', '.confirm-delete-form', function(e) {
    e.preventDefault();
    const form = $(this).closest('form')[0];
    const title = $(this).data('title') || '¿Deseas continuar?';
    const text = $(this).data('text') || 'Confirma si deseas continuar con esta acción.';
    window.AppConfirm({ title, text, icon: 'warning', confirmText: 'Continuar', cancelText: 'Cancelar', confirmColor: '#ef4444' })
        .then(result => { if (result.isConfirmed && form) form.requestSubmit(); });
});

/**
 * Confirmación para enlaces con clase .confirm-delete
 */
$(document).on('click', '.confirm-delete', function(e) {
    e.preventDefault();
    const url = $(this).attr('href');
    const title = $(this).data('title') || '¿Deseas continuar?';
    const text = $(this).data('text') || 'Confirma si deseas continuar con esta acción.';
    window.AppConfirm({ title, text, icon: 'warning', confirmText: 'Continuar', cancelText: 'Cancelar', confirmColor: '#ef4444' })
        .then(result => {
            if (result.isConfirmed) window.AppAjaxNavigation.navigate(url);
        });
});

/**
 * Confirmación para enlaces con clase .confirm-delete-link
 */
$(document).on('click', '.confirm-delete-link', function(e) {
    e.preventDefault();
    const url = $(this).attr('href');
    const title = $(this).data('title') || '¿Deseas continuar?';
    const text = $(this).data('text') || 'Confirma si deseas continuar con esta acción.';
    window.AppConfirm({ title, text, icon: 'warning', confirmText: 'Continuar', cancelText: 'Cancelar', confirmColor: '#ef4444' })
        .then(result => {
            if (result.isConfirmed) window.AppAjaxNavigation.navigate(url);
        });
});

/**
 * Confirmación de eliminación para botones con clase .confirm-delete-btn
 * El botón debe estar dentro de un formulario
 * @param {Event} e - Evento click
 */
$(document).on('click', '.confirm-delete-btn', function(e) {
    e.preventDefault();
    const btn   = $(this);
    const form  = btn.closest('form');
    const title = btn.data('title') || '¿Estás seguro?';
    const text  = btn.data('text')  || 'Esta acción no se puede deshacer.';
    Swal.fire({
        title, text, icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#ef4444', cancelButtonColor: '#6c757d',
        confirmButtonText: 'Sí, continuar', cancelButtonText: 'Cancelar',
        background: '#1a1a1a', color: '#ffffff',
        customClass: { popup: 'rounded-4 border-white-10 shadow-2xl' }
    }).then(result => { if (result.isConfirmed) form[0].requestSubmit(); });
});

/* =====================================================================
   Detección de Tablas Desplazables en Móviles
   ===================================================================== */

/**
 * Detecta si una tabla es desplazable horizontalmente en móviles
 * y añade una clase para indicar al usuario que puede desplazarse
 */
function initTableScrollability() {
    const tableResponsives = document.querySelectorAll('.table-responsive');

    tableResponsives.forEach(container => {
        container.classList.toggle('is-scrollable', container.scrollWidth > container.clientWidth);
    });

}

// Inicializar al cargar la página
window.AppPageLifecycle.onPageLoad(initTableScrollability);
window.addEventListener('resize', initTableScrollability, { passive: true });

// Reinicializar después de que DataTables redibuje las tablas
$(document).on('draw.dt', function() {
    initTableScrollability();
});
