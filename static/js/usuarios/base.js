
AOS.init({
    duration: 800,
    once: true,
    easing: 'ease-in-out'
});

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

$(document).on('input', '.numeric-only', function() {
    this.value = this.value.replace(/[^0-9]/g, '');
});

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
