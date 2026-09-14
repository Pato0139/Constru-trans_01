/**
 * Inicializa los eventos de la página de facturación
 */
document.addEventListener('DOMContentLoaded', function() {
    // Bootstrap modals must not remain inside scrolling/animated page containers.
    const modalPago = document.getElementById('modalPago');
    if (modalPago && modalPago.parentElement !== document.body) {
        document.body.appendChild(modalPago);
    }

    // Botones ver historial
    document.querySelectorAll('.btn-ver-historial').forEach(btn => {
        btn.addEventListener('click', function() {
            const numero = this.dataset.numero;
            const id = this.dataset.id;
            verHistorial(numero, id);
        });
    });

    // Botones abrir modal pago
    document.querySelectorAll('.btn-abrir-modal-pago').forEach(btn => {
        btn.addEventListener('click', function() {
            const id = this.dataset.id;
            const numero = this.dataset.numero;
            const saldo = this.dataset.saldo;
            abrirModalPago(id, numero, saldo);
        });
    });

    // Filter form submit automatically on any filter change
    const filterForm = document.getElementById('filterForm');
    if (filterForm) {
        const filterFields = filterForm.querySelectorAll('input.filter-input, select.filter-select');

        let submitTimer = null;
        const submitFilters = () => {
            clearTimeout(submitTimer);
            submitTimer = setTimeout(() => {
                filterForm.requestSubmit ? filterForm.requestSubmit() : filterForm.submit();
            }, 250);
        };

        filterFields.forEach(field => {
            const eventName = field.tagName === 'SELECT' ? 'change' : 'input';
            field.addEventListener(eventName, submitFilters);
        });
    }

    // Inicializar DataTables sin búsqueda ni menú de cantidad para la tabla de facturas
    if ($.fn.DataTable.isDataTable('#tablaFacturas')) {
        $('#tablaFacturas').DataTable().destroy();
    }
    
    $('#tablaFacturas').DataTable({
        "language": {
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
        "dom": 'rt<"d-flex justify-content-between align-items-center flex-wrap gap-3 mt-4 p-3"ip>',
        "order": [],
        "ordering": false // Opcional: si ya viene ordenado del backend y no queremos flechitas extra, sino dejarlo true
    });

    // Formulario pago
    const formPago = document.getElementById('formPago');
    if (formPago) {
        formPago.addEventListener('submit', function(e) {
            e.preventDefault();
            const formData = new FormData(this);
            const submitBtn = formPago.querySelector('button[type="submit"]');
            const originalText = submitBtn.innerHTML;
            
            // Estado de carga
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Procesando...';
            
            fetch(this.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': formData.get('csrfmiddlewaretoken')
                }
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Error en la respuesta del servidor');
                }
                return response.json();
            })
            .then(data => {
                if (data.status === 'ok') {
                    Swal.fire({
                        icon: 'success',
                        title: 'Pago Registrado',
                        text: data.mensaje,
                        confirmButtonColor: '#f59e0b',
                        background: '#161a22',
                        color: '#fff'
                    }).then(() => {
                        location.reload();
                    });
                } else {
                    Swal.fire({
                        icon: 'error',
                        title: 'Error',
                        text: data.error,
                        confirmButtonColor: '#f59e0b',
                        background: '#161a22',
                        color: '#fff'
                    });
                }
            })
            .catch(error => {
                console.error('Error:', error);
                Swal.fire({
                    icon: 'error',
                    title: 'Error de conexión',
                    text: 'No se pudo registrar el pago. Inténtalo de nuevo.',
                    confirmButtonColor: '#f59e0b',
                    background: '#161a22',
                    color: '#fff'
                });
            })
            .finally(() => {
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalText;
            });
        });
    }

});

/**
 * Formatea un valor numérico como moneda
 * @param {number|string} value - Valor a formatear
 * @returns {string} Valor formateado con separadores de miles
 */
function formatCurrency(value) {
    const val = Number(String(value).replace(',', '.'));
    if (!Number.isFinite(val)) {
        return '0';
    }
    return new Intl.NumberFormat('es-CO', {
        maximumFractionDigits: 2,
    }).format(val);
}

/**
 * Abre el modal de pago con los datos de la factura
 * @param {number|string} id - ID de la factura
 * @param {string} numero - Número de factura
 * @param {number|string} saldo - Saldo pendiente
 */
function abrirModalPago(id, numero, saldo) {
    document.getElementById('modalFacturaId').value = id;
    document.getElementById('modalFacturaNum').innerText = numero;

    document.getElementById('displayMonto').innerText = formatCurrency(saldo);
    const monto = Number(String(saldo).replace(',', '.'));
    document.getElementById('modalMonto').value = Number.isFinite(monto) ? monto.toFixed(2) : '';

    const modalElement = document.getElementById('modalPago');
    let modal = bootstrap.Modal.getInstance(modalElement);
    if (!modal) {
        modal = new bootstrap.Modal(modalElement);
    }
    modal.show();
}

/**
 * Redirige a la página de historial de pagos
 * @param {string} numero - Número de factura
 * @param {number|string} id - ID de la factura
 */
function verHistorial(numero, id) {
    const url = new URL(pagosHistorialUrl, window.location.origin);
    url.searchParams.set('q', numero);
    window.location.href = url.toString();
}
