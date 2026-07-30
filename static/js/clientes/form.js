/**
 * @file Gestión de formularios de pedidos de clientes con manejo dinámico de materiales
 * @description Permite agregar materiales dinámicamente, calcular totales y gestionar fechas de entrega
 */

/**
 * Total general acumulado del pedido
 * @type {number}
 * @global
 */
let totalGeneral = 0;

/**
 * Formatea un valor numérico como moneda colombiana
 * @function formatCurrency
 * @param {number|string} value - Valor a formatear
 * @returns {string} Valor formateado con símbolo de peso colombiano y separadores de miles
 * @example
 * formatCurrency(150000) // Returns "$150.000,00"
 */
function formatCurrency(value) {
    const val = parseFloat(value || 0);
    const formatted = val.toLocaleString('en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
    const res = formatted.replace(/,/g, 'X').replace(/\./g, ',').replace(/X/g, '.');
    return '$' + res;
}

/**
 * Actualiza el display del total general en el DOM
 * @function actualizarTotalDisplay
 * @description Busca el elemento con ID 'display-total' y actualiza su contenido con el total formateado
 * @returns {void}
 */
function actualizarTotalDisplay() {
    const totalElement = document.getElementById('display-total');
    if (totalElement) {
        totalElement.innerText = formatCurrency(totalGeneral);
    }
}

/**
 * Elimina una fila de material de la tabla y actualiza el total
 * @function eliminarFila
 * @param {HTMLElement} btn - Botón de eliminación clickeado
 * @param {number} subtotal - Subtotal de la fila a eliminar
 * @returns {void}
 * @description Remueve la fila del DOM y resta el subtotal del total general
 */
function eliminarFila(btn, subtotal) {
    btn.closest('tr')?.remove();
    totalGeneral = Math.round((totalGeneral - subtotal) * 100) / 100;
    actualizarTotalDisplay();
}

/**
 * Agrega un nuevo material a la tabla de detalles del pedido
 * @function agregarMaterial
 * @returns {void}
 * @description Valida selección y cantidad, calcula subtotal, crea fila HTML y actualiza el total
 * @fires Event#change - Dispara evento change en inputs para notificar cambios
 */
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

/**
 * Convierte una fecha en formato local a ISO 8601
 * @function parseToIso
 * @param {string} value - Fecha en formato DD/MM/YYYY HH:MM o variantes
 * @returns {string|null} Fecha en formato ISO 8601 (YYYY-MM-DDTHH:MM) o null si es inválida
 * @description Soporta múltiples formatos de entrada con separadores variados y AM/PM
 * @example
 * parseToIso("25/12/2024 14:30") // Returns "2024-12-25T14:30"
 * parseToIso("25.12.2024 2:30 PM") // Returns "2024-12-25T14:30"
 */
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

/**
 * Abre el selector de fecha/hora para el campo de fecha de entrega
 * @function openFechaEntregaPicker
 * @returns {void}
 * @description Sincroniza el campo visible con el picker oculto y activa el selector nativo
 * @see {@link formatFechaParaInput} para el formateo inverso
 */
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

/**
 * Formatea una fecha ISO para mostrar en el input de texto
 * @function formatFechaParaInput
 * @param {string} value - Fecha en formato ISO 8601
 * @returns {string} Fecha formateada como DD/MM/YYYY HH:MM para visualización humana
 * @description Convierte fecha ISO a formato local legible
 * @example
 * formatFechaParaInput("2024-12-25T14:30") // Returns "25/12/2024 14:30"
 */
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

/**
 * Inicializa eventos del formulario cuando el DOM está listo
 * @listens DOMContentLoaded
 */
document.addEventListener('DOMContentLoaded', () => {
    const totalInicial = document.getElementById('display-total')?.dataset.totalInicial;
    totalGeneral = parseFloat(totalInicial || 0);

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
