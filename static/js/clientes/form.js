
let totalGeneral = 0;

function formatCurrency(value) {
    const val = parseFloat(value || 0);
    const formatted = val.toLocaleString('en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
    const res = formatted.replace(/,/g, 'X').replace(/\./g, ',').replace(/X/g, '.');
    return '$' + res;
}

function actualizarTotalDisplay() {
    const totalElement = document.getElementById('display-total');
    if (totalElement) {
        totalElement.innerText = formatCurrency(totalGeneral);
    }
}

function calcularTotalDesdeFilas() {
    const botones = document.querySelectorAll('#lista-detalles .btn-eliminar-material');
    let total = 0;
    botones.forEach((btn) => {
        total += parseFloat(btn.dataset.subtotal || 0);
    });
    return Math.round(total * 100) / 100;
}

function eliminarFila(btn, subtotal) {
    btn.closest('tr')?.remove();
    totalGeneral = Math.round((totalGeneral - subtotal) * 100) / 100;
    actualizarTotalDisplay();
}

function agregarMaterial() {
    const select = document.getElementById('select-material');
    const cantidadInput = document.getElementById('input-cantidad');
    const lista = document.getElementById('lista-detalles');

    if (!select || !cantidadInput || !lista) return;

    const materialId = select.value;
    const materialNombre = select.options[select.selectedIndex]?.text || '';
    const precio = parseFloat(select.options[select.selectedIndex]?.getAttribute('data-precio') || 0);
    const cantidad = parseInt(cantidadInput.value || 0, 10);

    if (!materialId || cantidad <= 0) {
        alert('Seleccione un material y una cantidad válida');
        return;
    }

    const subtotal = Math.round(precio * cantidad * 100) / 100;
    totalGeneral = Math.round((totalGeneral + subtotal) * 100) / 100;

    const row = document.createElement('tr');
    row.className = 'material-item';
    row.innerHTML = `
        <td class="ps-0 py-3">
            <span class="text-white fw-600">${materialNombre}</span>
            <input type="hidden" name="material_id[]" value="${materialId}">
        </td>
        <td class="text-center text-white-50 py-3">
            <span class="badge rounded-pill px-3 material-badge">${cantidad}</span>
            <input type="hidden" name="cantidad[]" value="${cantidad}">
        </td>
        <td class="text-end text-accent fw-800 py-3">${formatCurrency(subtotal)}</td>
        <td class="text-end pe-0 py-3">
            <button type="button" class="btn btn-link text-danger p-0 btn-eliminar-material" data-subtotal="${subtotal}">
                <i class="bi bi-trash3-fill"></i>
            </button>
        </td>
    `;

    lista.appendChild(row);
    actualizarTotalDisplay();

    select.value = '';
    cantidadInput.value = 1;
}

function parseToIso(value) {
    if (!value) return null;

    const isoPattern = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/;
    if (isoPattern.test(value)) return value;

    const normalized = value.replace(/\.|-/g, '/').replace(/\s+/g, ' ').trim();
    const parts = normalized.split(' ');
    const datePart = parts[0] || '';
    const timePart = parts[1] || '00:00';

    const dateMatch = datePart.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
    if (!dateMatch) return null;

    let [, day, month, year] = dateMatch;
    day = day.padStart(2, '0');
    month = month.padStart(2, '0');

    const timeMatch = timePart.match(/^(\d{1,2}):(\d{2})(?:\s*(am|pm))?$/i);
    if (!timeMatch) return `${year}-${month}-${day}T00:00`;

    let [, hour, minute, ampm] = timeMatch;
    hour = Number(hour);

    if (ampm) {
        ampm = ampm.toLowerCase();
        if (ampm === 'pm' && hour < 12) hour += 12;
        if (ampm === 'am' && hour === 12) hour = 0;
    }

    hour = String(hour).padStart(2, '0');
    return `${year}-${month}-${day}T${hour}:${minute}`;
}

function openFechaEntregaPicker() {
    const visible = document.getElementById('fecha_entrega_text');
    const picker = document.getElementById('fecha_entrega_picker');
    if (!visible || !picker) return;

    const parsedIso = parseToIso(visible.value.trim());
    if (parsedIso) picker.value = parsedIso;

    if (picker.showPicker) {
        picker.showPicker();
    } else {
        picker.focus();
        try { picker.click(); } catch (error) {}
    }
}

function formatFechaParaInput(value) {
    if (!value) return '';

    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;

    const day = String(date.getDate()).padStart(2, '0');
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const year = date.getFullYear();
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');

    return `${day}/${month}/${year} ${hours}:${minutes}`;
}

document.addEventListener('DOMContentLoaded', () => {
    const totalInicial = document.getElementById('display-total')?.dataset.totalInicial;
    const totalDesdeFilas = calcularTotalDesdeFilas();
    const filasMateriales = document.querySelectorAll('#lista-detalles tr.material-item').length;

    if (!Number.isNaN(totalDesdeFilas) && filasMateriales > 0) {
        totalGeneral = totalDesdeFilas;
    } else {
        totalGeneral = filasMateriales > 0 ? 0 : parseFloat(totalInicial || 0);
    }

    document.getElementById('btn-agregar-material')
        ?.addEventListener('click', agregarMaterial);

    document.getElementById('btn-fecha-entrega')
        ?.addEventListener('click', openFechaEntregaPicker);

    document.getElementById('fecha_entrega_text')
        ?.addEventListener('click', openFechaEntregaPicker);

    document.getElementById('fecha_entrega_picker')
        ?.addEventListener('input', function () {
            const visibleField = document.getElementById('fecha_entrega_text');
            if (visibleField) visibleField.value = formatFechaParaInput(this.value);
        });

    document.addEventListener('click', (event) => {
        const btnEliminar = event.target.closest('.btn-eliminar-material');
        if (!btnEliminar) return;

        const subtotal = parseFloat(btnEliminar.dataset.subtotal || 0);
        eliminarFila(btnEliminar, subtotal);
    });

    actualizarTotalDisplay();
});
