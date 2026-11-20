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
    const stockDisponible = parseInt(select.options[select.selectedIndex]?.dataset.stock || 0, 10);
    const cantidad = parseInt(cantidadInput.value || 0, 10);

    if (!materialId || cantidad <= 0) {
        alert('Seleccione un material y una cantidad válida');
        return;
    }

    if (cantidad > stockDisponible) {
        alert(`Stock insuficiente. Solo hay ${stockDisponible} unidades disponibles de este material.`);
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
        <td class="text-end text-white-50 py-3">${formatCurrency(precio)}</td>
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
    cantidadInput.removeAttribute('max');
    const search = document.getElementById('material-search');
    if (search) search.value = '';
    cerrarSelectorMaterial();
    actualizarStockDisponible();
}

function actualizarStockDisponible() {
    const select = document.getElementById('select-material');
    const cantidadInput = document.getElementById('input-cantidad');
    const stockInfo = document.getElementById('disponibilidad-stock');
    if (!select || !cantidadInput || !stockInfo) return;

    const option = select.options[select.selectedIndex];
    if (!select.value || !option) {
        stockInfo.hidden = true;
        cantidadInput.removeAttribute('max');
        return;
    }

    const stock = parseInt(option.dataset.stock, 10) || 0;
    const minimo = parseInt(option.dataset.stockMinimo, 10) || 0;
    const unidad = option.dataset.unit || 'unidades';
    const cantidad = parseInt(cantidadInput.value, 10) || 0;
    const estado = obtenerEstadoStock(stock, minimo);
    cantidadInput.max = stock;
    stockInfo.hidden = false;
    stockInfo.replaceChildren();
    const cantidadLabel = document.createElement('span');
    cantidadLabel.textContent = `Existencias: ${stock} ${unidad}`;
    const estadoBadge = document.createElement('span');
    estadoBadge.className = `material-stock-badge stock-state--${estado.clase}`;
    estadoBadge.textContent = estado.texto;
    stockInfo.append(cantidadLabel, estadoBadge);
    if (cantidad > stock) {
        const aviso = document.createElement('span');
        aviso.className = 'text-danger';
        aviso.textContent = `La cantidad supera las existencias por ${cantidad - stock} ${unidad}.`;
        stockInfo.append(aviso);
    }
}

function obtenerEstadoStock(stock, minimo) {
    if (stock <= 0) return { clase: 'empty', texto: 'Sin existencias' };
    if (minimo > 0 && stock <= Math.ceil(minimo / 2)) return { clase: 'critical', texto: 'Stock crítico' };
    if (minimo > 0 && stock <= minimo) return { clase: 'low', texto: 'Stock bajo' };
    return { clase: 'sufficient', texto: 'Stock suficiente' };
}

function cerrarSelectorMaterial() {
    const opciones = document.getElementById('material-options');
    const busqueda = document.getElementById('material-search');
    if (opciones) opciones.hidden = true;
    busqueda?.setAttribute('aria-expanded', 'false');
}

function renderizarOpcionesMateriales(filtro = '') {
    const select = document.getElementById('select-material');
    const lista = document.getElementById('material-options');
    if (!select || !lista) return;
    const termino = filtro.trim().toLocaleLowerCase();
    lista.replaceChildren();

    Array.from(select.options).slice(1).forEach((option) => {
        if (!option.text.toLocaleLowerCase().includes(termino)) return;
        const stock = parseInt(option.dataset.stock, 10) || 0;
        const minimo = parseInt(option.dataset.stockMinimo, 10) || 0;
        const estado = obtenerEstadoStock(stock, minimo);
        const fila = document.createElement('button');
        fila.type = 'button';
        fila.className = 'material-option';
        fila.setAttribute('role', 'option');
        fila.setAttribute('aria-selected', String(select.value === option.value));

        const detalle = document.createElement('span');
        detalle.className = 'material-option__details';
        const nombre = document.createElement('span');
        nombre.className = 'material-option__name';
        nombre.textContent = option.text;
        nombre.title = option.text;
        const precio = document.createElement('span');
        precio.className = 'material-option__price';
        precio.textContent = `Precio unitario: ${formatCurrency(option.dataset.precio)}`;
        detalle.append(nombre, precio);

        const insignia = document.createElement('span');
        insignia.className = `material-stock-badge stock-state--${estado.clase}`;
        insignia.textContent = `${estado.texto}: ${stock} ${option.dataset.unit || 'unid.'}`;
        insignia.title = estado.texto;
        fila.append(detalle, insignia);
        fila.addEventListener('click', () => {
            select.value = option.value;
            const busqueda = document.getElementById('material-search');
            if (busqueda) busqueda.value = option.text;
            select.dispatchEvent(new Event('change', { bubbles: true }));
            cerrarSelectorMaterial();
        });
        lista.appendChild(fila);
    });

    if (!lista.children.length) {
        const vacio = document.createElement('div');
        vacio.className = 'material-options__empty';
        vacio.textContent = 'No se encontraron materiales.';
        lista.appendChild(vacio);
    }
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
    if (!picker) return;

    if (visible && visible.value.trim()) {
        const parsedIso = parseToIso(visible.value.trim());
        if (parsedIso) picker.value = parsedIso;
    }

    try {
        if (typeof picker.showPicker === 'function') {
            picker.showPicker();
            return;
        }
    } catch (e) {
        console.warn('showPicker no disponible:', e);
    }

    try {
        picker.click();
    } catch (e) {}
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

    const parts = value.split('T');
    if (parts.length === 2) {
        const [datePart, timePart] = parts;
        const [year, month, day] = datePart.split('-');
        if (year && month && day) {
            const time = timePart.slice(0, 5);
            return `${day.padStart(2, '0')}/${month.padStart(2, '0')}/${year} ${time}`;
        }
    }

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
window.AppPageLifecycle.onPageLoad(() => {
    const totalInicial = document.getElementById('display-total')?.dataset.totalInicial;
    totalGeneral = parseFloat(totalInicial || 0);

    document.getElementById('btn-agregar-material')
        ?.addEventListener('click', agregarMaterial);

    document.getElementById('select-material')
        ?.addEventListener('change', actualizarStockDisponible);
    document.getElementById('input-cantidad')
        ?.addEventListener('input', actualizarStockDisponible);

    const busquedaMaterial = document.getElementById('material-search');
    const opcionesMaterial = document.getElementById('material-options');
    if (busquedaMaterial && opcionesMaterial) {
        const abrirOpciones = () => {
            const seleccionado = document.querySelector('#select-material option:checked');
            if (seleccionado?.value && busquedaMaterial.value === seleccionado.text) {
                busquedaMaterial.value = '';
            }
            renderizarOpcionesMateriales(busquedaMaterial.value);
            opcionesMaterial.hidden = false;
            busquedaMaterial.setAttribute('aria-expanded', 'true');
        };
        busquedaMaterial.addEventListener('focus', abrirOpciones);
        busquedaMaterial.addEventListener('click', abrirOpciones);
        busquedaMaterial.addEventListener('input', () => {
            renderizarOpcionesMateriales(busquedaMaterial.value);
            opcionesMaterial.hidden = false;
            busquedaMaterial.setAttribute('aria-expanded', 'true');
        });
        busquedaMaterial.addEventListener('keydown', (event) => {
            if (event.key === 'Escape') cerrarSelectorMaterial();
            if (event.key === 'ArrowDown') opcionesMaterial.querySelector('button')?.focus();
        });
        opcionesMaterial.addEventListener('keydown', (event) => {
            const filas = Array.from(opcionesMaterial.querySelectorAll('button'));
            const indice = filas.indexOf(document.activeElement);
            if (event.key === 'ArrowDown') { event.preventDefault(); filas[Math.min(indice + 1, filas.length - 1)]?.focus(); }
            if (event.key === 'ArrowUp') { event.preventDefault(); (filas[Math.max(indice - 1, 0)] || busquedaMaterial).focus(); }
            if (event.key === 'Escape') { cerrarSelectorMaterial(); busquedaMaterial.focus(); }
        });
        document.addEventListener('click', (event) => {
            if (!event.target.closest('.material-picker')) cerrarSelectorMaterial();
        });
    }

    const picker = document.getElementById('fecha_entrega_picker');
    const visibleField = document.getElementById('fecha_entrega_text');
    const btnPicker = document.getElementById('btn-fecha-entrega');

    btnPicker?.addEventListener('click', openFechaEntregaPicker);

    visibleField?.addEventListener('click', function () {
        if (!this.value.trim()) {
            openFechaEntregaPicker();
        }
    });

    function syncPickerToText() {
        if (visibleField && picker && picker.value) {
            visibleField.value = formatFechaParaInput(picker.value);
        }
    }

    picker?.addEventListener('input', syncPickerToText);
    picker?.addEventListener('change', syncPickerToText);

    visibleField?.addEventListener('input', function () {
        if (picker && this.value.trim()) {
            const parsedIso = parseToIso(this.value.trim());
            if (parsedIso) {
                picker.value = parsedIso;
            }
        }
    });

    document.addEventListener('click', (event) => {
        const btnEliminar = event.target.closest('.btn-eliminar-material');
        if (!btnEliminar) return;

        const subtotal = parseFloat(btnEliminar.dataset.subtotal || 0);
        eliminarFila(btnEliminar, subtotal);
    });

    actualizarTotalDisplay();
});
