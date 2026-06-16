document.addEventListener('DOMContentLoaded', function() {
    // Botones ver historial
    document.querySelectorAll('.btn-ver-historial-mis-facturas').forEach(btn => {
        btn.addEventListener('click', function() {
            const numero = this.dataset.numero;
            const id = this.dataset.id;
            verHistorial(numero, id);
        });
    });

    // Botones abrir modal pago
    document.querySelectorAll('.btn-abrir-modal-pago-mis-facturas').forEach(btn => {
        btn.addEventListener('click', function() {
            const id = this.dataset.id;
            const numero = this.dataset.numero;
            const total = this.dataset.total;
            abrirModalPago(id, numero, total);
        });
    });

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
                        title: '¡Pago Exitoso!',
                        text: 'Tu pago ha sido registrado y el administrador ha sido notificado.',
                        background: '#1a1a1a', 
                        color: '#fff', 
                        confirmButtonColor: '#f39c12'
                    }).then(() => location.reload());
                } else {
                    Swal.fire({
                        icon: 'error',
                        title: 'Error',
                        text: data.error,
                        background: '#1a1a1a', 
                        color: '#fff'
                    });
                }
            });
        });
    }
});

let pagosData = {};

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

function verHistorial(numero, id) {
    document.getElementById('historialFacturaNum').innerText = numero;
    const lista = document.getElementById('listaPagos');
    lista.innerHTML = '';
    
    const pagos = pagosData[id] || [];
    
    if (pagos.length === 0) {
        lista.innerHTML = '<tr><td colspan="4" class="text-center py-4 text-white-50">Aún no has realizado pagos para esta factura.</td></tr>';
    } else {
        pagos.forEach(p => {
            lista.innerHTML += `
                <tr>
                    <td class="ps-4 small text-white-50">${p.fecha}</td>
                    <td><span class="badge bg-dark border border-white-10 text-white">${p.metodo}</span></td>
                    <td class="small text-white-50">${p.referencia}</td>
                    <td class="text-end pe-4 fw-bold text-accent">${p.monto}</td>
                </tr>
            `;
        });
    }
    
    new bootstrap.Modal(document.getElementById('modalHistorial')).show();
}

function abrirModalPago(id, numero, total) {
    document.getElementById('modalFacturaId').value = id;
    document.getElementById('modalFacturaNum').innerText = numero;
    
    document.getElementById('displayMonto').innerText = formatCurrency(total);
    document.getElementById('modalMonto').value = total;
    
    new bootstrap.Modal(document.getElementById('modalPago')).show();
}
