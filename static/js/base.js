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
if (sidebarToggle) {
    sidebarToggle.addEventListener('click', () => {
        sidebar.classList.add('active');
        sidebarOverlay.classList.add('active');
        document.body.style.overflow = 'hidden';
    });
}

/** Cierra el sidebar desde el botón interno */
if (sidebarClose) {
    sidebarClose.addEventListener('click', () => {
        sidebar.classList.remove('active');
        sidebarOverlay.classList.remove('active');
        document.body.style.overflow = 'auto';
    });
}

/** Cierra el sidebar al hacer clic en el overlay */
if (sidebarOverlay) {
    sidebarOverlay.addEventListener('click', () => {
        sidebar.classList.remove('active');
        sidebarOverlay.classList.remove('active');
        document.body.style.overflow = 'auto';
    });
}

// Redirigir errores de DataTables a la consola en vez de ventanas emergentes
$.fn.dataTable.ext.errMode = 'throw';

/* =====================================================================
   DataTables
   ===================================================================== */
$(document).ready(function() {
    /**
     * Inicializa DataTables en todas las tablas que no tengan la clase .no-datatable
     */
    $('.table:not(.no-datatable)').DataTable({
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
        dom: '<"d-flex justify-content-between align-items-center flex-wrap gap-3 mb-3"lf>rt<"d-flex justify-content-between align-items-center flex-wrap gap-3 mt-4"ip>'
    });

    /**
     * Muestra mensajes de Django usando SweetAlert2 toast
     * Los mensajes se inyectan desde el div #django-messages-data
     */
    const djangoMessagesDiv = document.getElementById('django-messages-data');
    if (djangoMessagesDiv) {
        djangoMessagesDiv.querySelectorAll('.django-message-item').forEach(msgEl => {
            const tags = msgEl.dataset.tags;
            const text = msgEl.dataset.text;
            Swal.fire({
                icon:             tags === 'error' ? 'error' : (tags === 'success' ? 'success' : 'info'),
                title:            tags.charAt(0).toUpperCase() + tags.slice(1),
                text,
                toast:            true,
                position:         'top-end',
                showConfirmButton: false,
                timer:            5000,
                timerProgressBar: true,
                background:       '#1a1a1a',
                color:            '#ffffff',
                iconColor:        tags === 'success' ? '#10b981' : (tags === 'error' ? '#ef4444' : '#F39C12'),
                customClass:      { popup: 'rounded-4 border-white-10 shadow-2xl' }
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

/* =====================================================================
   Confirmaciones SweetAlert2
   ===================================================================== */

/**
 * Confirmación de cierre de sesión para elementos con clase .confirm-logout
 * @param {Event} e - Evento click
 */
$(document).on('click', '.confirm-logout', function(e) {
    e.preventDefault();
    const url = $(this).attr('href');
    Swal.fire({
        title: '¿Cerrar sesión?',
        text: '¿Estás seguro de que deseas salir del sistema?',
        icon: 'question',
        showCancelButton: true,
        confirmButtonColor: '#f97316',
        cancelButtonColor:  '#6c757d',
        confirmButtonText:  'Sí, salir',
        cancelButtonText:   'Cancelar',
        background: '#1a1a1a',
        color:      '#ffffff',
        customClass: { popup: 'rounded-4 border-white-10 shadow-2xl' }
    }).then(result => { if (result.isConfirmed) window.location.href = url; });
});

/**
 * Confirmación de eliminación para formularios con clase .confirm-delete-form
 * @param {Event} e - Evento click
 */
$(document).on('click', '.confirm-delete-form', function(e) {
    e.preventDefault();
    const form  = $(this).closest('form');
    const title = $(this).data('title') || '¿Estás seguro?';
    const text  = $(this).data('text')  || 'Esta acción no se puede deshacer.';
    Swal.fire({
        title, text, icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#ef4444', cancelButtonColor: '#6c757d',
        confirmButtonText: 'Sí, continuar', cancelButtonText: 'Cancelar',
        background: '#1a1a1a', color: '#ffffff',
        customClass: { popup: 'rounded-4 border-white-10 shadow-2xl' }
    }).then(result => { if (result.isConfirmed) form.submit(); });
});

/**
 * Confirmación de eliminación para enlaces con clase .confirm-delete
 * @param {Event} e - Evento click
 */
$(document).on('click', '.confirm-delete', function(e) {
    e.preventDefault();
    const url   = $(this).attr('href');
    const title = $(this).data('title') || '¿Estás seguro?';
    const text  = $(this).data('text')  || 'Esta acción no se puede deshacer.';
    Swal.fire({
        title, text, icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#ef4444', cancelButtonColor: '#6c757d',
        confirmButtonText: 'Sí, eliminar', cancelButtonText: 'Cancelar',
        background: '#1a1a1a', color: '#ffffff',
        customClass: { popup: 'rounded-4 border-white-10 shadow-2xl' }
    }).then(result => { if (result.isConfirmed) window.location.href = url; });
});

/**
 * Confirmación de eliminación para enlaces con clase .confirm-delete-link
 * @param {Event} e - Evento click
 */
$(document).on('click', '.confirm-delete-link', function(e) {
    e.preventDefault();
    const url   = $(this).attr('href');
    const title = $(this).data('title') || '¿Estás seguro?';
    const text  = $(this).data('text')  || 'Esta acción no se puede deshacer.';
    Swal.fire({
        title, text, icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#ef4444', cancelButtonColor: '#6c757d',
        confirmButtonText: 'Sí, continuar', cancelButtonText: 'Cancelar',
        background: '#1a1a1a', color: '#ffffff',
        customClass: { popup: 'rounded-4 border-white-10 shadow-2xl' }
    }).then(result => { if (result.isConfirmed) window.location.href = url; });
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
    }).then(result => { if (result.isConfirmed) form.submit(); });
});
