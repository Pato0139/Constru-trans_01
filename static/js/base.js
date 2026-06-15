
// Initialize AOS
AOS.init({
    duration: 800,
    once: true,
    easing: 'ease-in-out'
});

// Sidebar Toggle Functionality
const sidebarToggle = document.getElementById('sidebarToggle');
const sidebarClose = document.getElementById('sidebarClose');
const sidebar = document.getElementById('sidebar');
const sidebarOverlay = document.getElementById('sidebarOverlay');

if (sidebarToggle) {
    sidebarToggle.addEventListener('click', () => {
        sidebar.classList.add('active');
        sidebarOverlay.classList.add('active');
        document.body.style.overflow = 'hidden';
    });
}

if (sidebarClose) {
    sidebarClose.addEventListener('click', () => {
        sidebar.classList.remove('active');
        sidebarOverlay.classList.remove('active');
        document.body.style.overflow = 'auto';
    });
}

if (sidebarOverlay) {
    sidebarOverlay.addEventListener('click', () => {
        sidebar.classList.remove('active');
        sidebarOverlay.classList.remove('active');
        document.body.style.overflow = 'auto';
    });
}

// Desactivar alertas de DataTables y redirigirlas a la consola para evitar ventanas emergentes
$.fn.dataTable.ext.errMode = 'throw';

$(document).ready(function() {
    $('.table:not(.no-datatable)').DataTable({
        "language": {
            "search": "Buscar:",
            "lengthMenu": "Mostrar _MENU_ registros por página",
            "zeroRecords": "No se encontraron resultados",
            "info": "Mostrando registros del _START_ al _END_ de un total de _TOTAL_ registros",
            "infoEmpty": "No hay registros disponibles",
            "infoFiltered": "(filtrado de _MAX_ registros totales)",
            "paginate": {
                "first": "Primero",
                "last": "Último",
                "next": "Siguiente",
                "previous": "Anterior"
            }
        },
        "pageLength": 10,
        "responsive": true,
        "dom": '<"d-flex justify-content-between align-items-center mb-3"lf>rt<"d-flex justify-content-between align-items-center mt-3"ip>'
    });

    // Custom SweetAlert for Django Messages
    // The messages data will be injected via django-messages-data div
    const djangoMessagesDiv = document.getElementById('django-messages-data');
    if (djangoMessagesDiv) {
        const messages = djangoMessagesDiv.querySelectorAll('.django-message-item');
        messages.forEach(msgEl => {
            const tags = msgEl.dataset.tags;
            const text = msgEl.dataset.text;
            
            Swal.fire({
                icon: tags === 'error' ? 'error' : (tags === 'success' ? 'success' : 'info'),
                title: tags.charAt(0).toUpperCase() + tags.slice(1),
                text: text,
                toast: true,
                position: 'top-end',
                showConfirmButton: false,
                timer: 5000,
                timerProgressBar: true,
                background: '#1a1a1a',
                color: '#ffffff',
                iconColor: tags === 'success' ? '#10b981' : (tags === 'error' ? '#ef4444' : '#F39C12'),
                customClass: {
                    popup: 'rounded-4 border-white-10 shadow-2xl'
                }
            });
        });
    }
});

// Global Input Validation
$(document).on('input', '.numeric-only', function() {
    this.value = this.value.replace(/[^0-9]/g, '');
});

$(document).on('input', '.decimal-only', function() {
    let value = this.value.replace(/[^0-9\.,]/g, '');
    value = value.replace(/,/g, '.');
    const parts = value.split('.');
    if (parts.length > 2) {
        value = parts.shift() + '.' + parts.join('');
    }
    if (value.includes('.')) {
        const [intPart, decPart] = value.split('.');
        value = intPart + '.' + decPart.slice(0, 2);
    }
    this.value = value;
});

$(document).on('input', '.alphanumeric-only', function() {
    this.value = this.value.replace(/[^a-zA-Z0-9]/g, '');
});

$(document).on('input', '.plate-only', function() {
    // Alfanumérico y mayúsculas para placas
    this.value = this.value.toUpperCase().replace(/[^A-Z0-9]/g, '');
});

// Global Logout Confirmation
$(document).on('click', '.confirm-logout', function(e) {
    e.preventDefault();
    const url = $(this).attr('href');
    
    Swal.fire({
        title: '¿Cerrar sesión?',
        text: '¿Estás seguro de que deseas salir del sistema?',
        icon: 'question',
        showCancelButton: true,
        confirmButtonColor: '#f97316',
        cancelButtonColor: '#6c757d',
        confirmButtonText: 'Sí, salir',
        cancelButtonText: 'Cancelar',
        background: '#1a1a1a',
        color: '#ffffff',
        customClass: {
            popup: 'rounded-4 border-white-10 shadow-2xl'
        }
    }).then((result) => {
        if (result.isConfirmed) {
            window.location.href = url;
        }
    });
});

// Global Delete Confirmation with SweetAlert2 (Forms)
$(document).on('click', '.confirm-delete-form', function(e) {
    e.preventDefault();
    const form = $(this).closest('form');
    const title = $(this).data('title') || '¿Estás seguro?';
    const text = $(this).data('text') || 'Esta acción no se puede deshacer.';
    
    Swal.fire({
        title: title,
        text: text,
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#ef4444',
        cancelButtonColor: '#6c757d',
        confirmButtonText: 'Sí, continuar',
        cancelButtonText: 'Cancelar',
        background: '#1a1a1a',
        color: '#ffffff',
        customClass: {
            popup: 'rounded-4 border-white-10 shadow-2xl'
        }
    }).then((result) => {
        if (result.isConfirmed) {
            form.submit();
        }
    });
});

// Global Delete Confirmation with SweetAlert2 (Links)
$(document).on('click', '.confirm-delete', function(e) {
    e.preventDefault();
    const url = $(this).attr('href');
    const title = $(this).data('title') || '¿Estás seguro?';
    const text = $(this).data('text') || 'Esta acción no se puede deshacer.';
    
    Swal.fire({
        title: title,
        text: text,
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#ef4444',
        cancelButtonColor: '#6c757d',
        confirmButtonText: 'Sí, eliminar',
        cancelButtonText: 'Cancelar',
        background: '#1a1a1a',
        color: '#ffffff',
        customClass: {
            popup: 'rounded-4 border-white-10 shadow-2xl'
        }
    }).then((result) => {
        if (result.isConfirmed) {
            window.location.href = url;
        }
    });
});
