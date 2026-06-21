document.addEventListener('DOMContentLoaded', function() {
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

    // Botones abrir modal editar
    document.querySelectorAll('.btn-abrir-modal-editar').forEach(btn => {
        btn.addEventListener('click', function() {
            const id = this.dataset.id;
            const numero = this.dataset.numero;
            const total = this.dataset.total;
            abrirModalEditar(id, numero, total);
        });
    });

    // Botones anular factura
    document.querySelectorAll('.btn-anular-factura').forEach(btn => {
        btn.addEventListener('click', function() {
            const id = this.dataset.id;
            const numero = this.dataset.numero;
            anularFactura(id, numero);
        });
    });

    // Filter form submit on select change
    const filterForm = document.getElementById('filterForm');
    if (filterForm) {
        const estadoSelect = filterForm.querySelector('select[name="estado"]');
        if (estadoSelect) {
            estadoSelect.addEventListener('change', function() {
                filterForm.submit();
            });
        }
    }

    // Formulario pago
    const formPago = document.getElementById('formPago');
    if (formPago) {
        formPago.addEventListener('submit', function(e) {
            e.preventDefault();
            const formData = new FormData(this);
            
            fetch(this.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': formData.get('csrfmiddlewaretoken')
                }
            })
            .then(response => response.json())
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
                    text: 'No se pudo registrar el pago',
                    confirmButtonColor: '#f59e0b',
                    background: '#161a22',
                    color: '#fff'
                });
            });
        });
    }

    // Formulario editar monto
    const formEditar = document.getElementById('formEditar');
    if (formEditar) {
        formEditar.addEventListener('submit', function(e) {
            e.preventDefault();
            const formData = new FormData(this);

            fetch(this.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': formData.get('csrfmiddlewaretoken')
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'ok') {
                    Swal.fire({
                        icon: 'success',
                        title: 'Actualizado',
                        text: data.mensaje,
                        background: '#161a22',
                        color: '#fff'
                    }).then(() => location.reload());
                } else {
                    Swal.fire('Error', data.error, 'error');
                }
            });
        });
    }
});

function formatCurrency(value) {
    let val = parseFloat(value);
    let rounded = Math.round(val);
    let s = String(rounded);
    let parts = [];
    while (s.length > 0) {
        parts.unshift(s.slice(-3));
        s = s.slice(0, -3);
    }
    return parts.join('.');
}

function abrirModalPago(id, numero, saldo) {
    document.getElementById('modalFacturaId').value = id;
    document.getElementById('modalFacturaNum').innerText = numero;

    document.getElementById('displayMonto').innerText = formatCurrency(saldo);
    document.getElementById('modalMonto').value = parseFloat(saldo);

    const modalElement = document.getElementById('modalPago');
    let modal = bootstrap.Modal.getInstance(modalElement);
    if (!modal) {
        modal = new bootstrap.Modal(modalElement);
    }
    modal.show();
}

function abrirModalEditar(id, numero, total) {
    document.getElementById('modalEditarId').value = id;
    document.getElementById('modalEditarNum').innerText = numero;

    document.getElementById('modalEditarMonto').value = parseFloat(total);

    const form = document.getElementById('formEditar');
    form.action = "/facturacion/editar-monto/" + id + "/";

    const modalElement = document.getElementById('modalEditar');
    let modal = bootstrap.Modal.getInstance(modalElement);
    if (!modal) {
        modal = new bootstrap.Modal(modalElement);
    }
    modal.show();
}

function anularFactura(id, numero) {
    Swal.fire({
        title: '¿Anular Factura?',
        text: "Esta acción marcará la factura " + numero + " como anulada.",
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#d33',
        cancelButtonColor: '#3085d6',
        confirmButtonText: 'Sí, anular',
        cancelButtonText: 'Cancelar',
        background: '#161a22',
        color: '#fff'
    }).then((result) => {
        if (result.isConfirmed) {
            fetch("/facturacion/anular/" + id + "/", {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'ok') {
                    Swal.fire({
                        icon: 'success',
                        title: 'Anulada',
                        text: data.mensaje,
                        background: '#161a22',
                        color: '#fff'
                    }).then(() => location.reload());
                } else {
                    Swal.fire('Error', data.error, 'error');
                }
            });
        }
    });
}

function verHistorial(numero, id) {
    window.location.href = "/pagos/?q=" + numero;
}
