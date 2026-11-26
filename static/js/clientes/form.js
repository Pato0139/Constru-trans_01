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
let stockRefreshTimer = null;
let stockRefreshInFlight = false;

function obtenerConfigDespacho() {
    const form = document.getElementById('form-pedido');
    return {
        ciudadGratis: (form?.dataset.ciudadGratis || 'Duitama').trim().toLocaleLowerCase(),
        tarifaExterna: parseFloat(form?.dataset.tarifaEnvio || '15000') || 15000,
        montoMinimo: parseFloat(form?.dataset.montoMinimo || '50000') || 50000,
    };
}

function obtenerCiudadSeleccionada() {
    const selectCiudad = document.getElementById('select-ciudad') || document.querySelector('select[name="ciudad"]');
    return (selectCiudad?.value || '').trim();
}

function calcularTarifaEnvio(ciudad) {
    const { ciudadGratis, tarifaExterna } = obtenerConfigDespacho();
    const ciudadNorm = (ciudad || '').trim().toLocaleLowerCase();
    if (!ciudadNorm) return 0;
    if (ciudadNorm === ciudadGratis) return 0;
    return tarifaExterna;
}

function calcularTotalConEnvio() {
    const tarifa = calcularTarifaEnvio(obtenerCiudadSeleccionada());
    return Math.round((totalGeneral + tarifa) * 100) / 100;
}

function parseStockNumber(value) {
    const normalized = String(value ?? '').replace(/[^\d-]/g, '');
    return Number.parseInt(normalized, 10) || 0;
}

/**
 * Formatea un valor numérico como moneda colombiana sin decimales innecesarios
 * @function formatCurrency
 * @param {number|string} value - Valor a formatear
 * @returns {string} Valor formateado con símbolo de peso colombiano y separadores de miles
 * @example
 * formatCurrency(150000) // Returns "$150.000"
 */
function formatCurrency(value) {
    const val = Math.round(parseFloat(value || 0) || 0);
    const formatted = val.toLocaleString('en-US', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    });
    const res = formatted.replace(/,/g, '.');
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
    const tarifaElement = document.getElementById('display-tarifa-envio');
    const tarifaDetalleElement = document.getElementById('display-tarifa-detalle');
    const alertaMinimo = document.getElementById('pedido-minimo-alerta');
    const alertaMinimoTexto = document.getElementById('pedido-minimo-texto');
    const btnConfirmar = document.getElementById('btn-confirmar-pedido');

    const { ciudadGratis, tarifaExterna, montoMinimo } = obtenerConfigDespacho();
    const ciudad = obtenerCiudadSeleccionada();
    const tarifaEnvio = calcularTarifaEnvio(ciudad);
    const totalConEnvio = Math.round((totalGeneral + tarifaEnvio) * 100) / 100;

    if (totalElement) {
        totalElement.innerText = formatCurrency(totalConEnvio);
    }

    if (tarifaElement) {
        tarifaElement.innerText = formatCurrency(tarifaEnvio);
        tarifaElement.classList.toggle('is-free', Boolean(ciudad) && tarifaEnvio === 0);
    }

    if (tarifaDetalleElement) {
        if (!ciudad) {
            tarifaDetalleElement.textContent = `Envío gratis en Duitama; otros destinos ${formatCurrency(tarifaExterna)}.`;
        } else if (ciudad.toLocaleLowerCase() === ciudadGratis) {
            tarifaDetalleElement.textContent = 'Envío gratis por destino en Duitama.';
        } else {
            tarifaDetalleElement.textContent = `Tarifa fija aplicada para envío a ${ciudad}.`;
        }
    }

    const cumpleMinimo = totalConEnvio >= montoMinimo;
    if (alertaMinimo && alertaMinimoTexto) {
        alertaMinimo.hidden = cumpleMinimo;
        if (!cumpleMinimo) {
            const faltante = Math.max(0, Math.round((montoMinimo - totalConEnvio) * 100) / 100);
            if (totalConEnvio > 0) {
                alertaMinimoTexto.textContent = `El pedido mínimo es de ${formatCurrency(montoMinimo)}. Te faltan ${formatCurrency(faltante)} para poder continuar al pago.`;
            } else {
                alertaMinimoTexto.textContent = `El pedido mínimo es de ${formatCurrency(montoMinimo)} para poder continuar al pago.`;
            }
        }
    }

    if (btnConfirmar) {
        btnConfirmar.disabled = !cumpleMinimo;
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
    const stockDisponible = parseStockNumber(select.options[select.selectedIndex]?.dataset.stock);
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

    const stock = parseStockNumber(option.dataset.stock);
    const minimo = parseStockNumber(option.dataset.stockMinimo);
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
        const stock = parseStockNumber(option.dataset.stock);
        const minimo = parseStockNumber(option.dataset.stockMinimo);
        const estado = obtenerEstadoStock(stock, minimo);
        const fila = document.createElement('button');
        fila.type = 'button';
        fila.className = 'material-option';
        fila.dataset.materialId = option.value;
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

async function actualizarExistenciasEnVivo() {
    const form = document.getElementById('form-pedido');
    const select = document.getElementById('select-material');
    const url = form?.dataset.stockUrl;
    if (!url || !select || stockRefreshInFlight || document.hidden) return;

    stockRefreshInFlight = true;
    try {
        const response = await fetch(url, {
            method: 'GET',
            credentials: 'same-origin',
            cache: 'no-store',
            headers: { Accept: 'application/json' }
        });
        if (!response.ok) throw new Error('No se pudo consultar el inventario.');
        const data = await response.json();
        let huboCambios = false;
        const lista = document.getElementById('material-options');
        const search = document.getElementById('material-search');
        const materialEnFoco = document.activeElement
            ?.closest('.material-option')
            ?.dataset.materialId;

        Array.from(select.options).slice(1).forEach((option) => {
            const stockActualizado = data.stocks?.[String(option.value)];
            if (!stockActualizado) return;
            const cantidad = Number(stockActualizado.cantidad);
            const minimo = Number(stockActualizado.minimo);
            if (!Number.isInteger(cantidad) || !Number.isInteger(minimo)) return;

            if (
                parseStockNumber(option.dataset.stock) !== cantidad
                || parseStockNumber(option.dataset.stockMinimo) !== minimo
            ) {
                huboCambios = true;
                option.dataset.stock = String(cantidad);
                option.dataset.stockMinimo = String(minimo);
            }
        });

        if (huboCambios) {
            actualizarStockDisponible();
            if (lista && !lista.hidden) {
                renderizarOpcionesMateriales(search?.value || '');
                if (materialEnFoco) {
                    Array.from(lista.querySelectorAll('.material-option'))
                        .find((option) => option.dataset.materialId === materialEnFoco)
                        ?.focus();
                }
            }
        }
    } catch (error) {
        // El servidor validará el stock al enviar el pedido.
    } finally {
        stockRefreshInFlight = false;
    }
}

function iniciarActualizacionExistencias() {
    const form = document.getElementById('form-pedido');
    if (!form?.dataset.stockUrl || form.dataset.stockLiveInitialized === 'true') return;
    form.dataset.stockLiveInitialized = 'true';

    actualizarExistenciasEnVivo();
    stockRefreshTimer = window.setInterval(actualizarExistenciasEnVivo, 5000);
    window.addEventListener('focus', actualizarExistenciasEnVivo);
    document.addEventListener('visibilitychange', () => {
        if (!document.hidden) actualizarExistenciasEnVivo();
    });
    window.addEventListener('pagehide', () => {
        if (stockRefreshTimer) window.clearInterval(stockRefreshTimer);
        stockRefreshTimer = null;
    }, { once: true });
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
    const displayTotal = document.getElementById('display-total');
    const subtotalInicial = displayTotal?.dataset.subtotalInicial ?? displayTotal?.dataset.totalInicial;
    totalGeneral = parseFloat(subtotalInicial || 0);

    document.getElementById('btn-agregar-material')
        ?.addEventListener('click', agregarMaterial);

    const selectCiudad = document.getElementById('select-ciudad') || document.querySelector('select[name="ciudad"]');
    selectCiudad?.addEventListener('change', actualizarTotalDisplay);

    const formPedido = document.getElementById('form-pedido');
    formPedido?.addEventListener('submit', (event) => {
        const { montoMinimo } = obtenerConfigDespacho();
        const totalConEnvio = calcularTotalConEnvio();
        if (totalConEnvio < montoMinimo) {
            event.preventDefault();
            actualizarTotalDisplay();
            document.getElementById('pedido-minimo-alerta')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    });

    document.getElementById('select-material')
        ?.addEventListener('change', actualizarStockDisponible);
    document.getElementById('input-cantidad')
        ?.addEventListener('input', actualizarStockDisponible);
    iniciarActualizacionExistencias();

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

// Evita que el navegador restaure un formulario de pedido viejo desde BFCache al usar el botón Atrás.
window.addEventListener('pageshow', (event) => {
    const navEntries = window.performance && typeof window.performance.getEntriesByType === 'function'
        ? window.performance.getEntriesByType('navigation')
        : [];
    const isBackForward = event.persisted || (navEntries.length > 0 && navEntries[0].type === 'back_forward');
    if (isBackForward && document.getElementById('form-pedido')) {
        window.location.reload();
    }
});
