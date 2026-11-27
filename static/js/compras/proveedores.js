/**
 * @file Gestión del formulario de catálogo de materiales de proveedores
 */

/**
 * Inicializa el formset de catálogo de proveedores
 * @listens DOMContentLoaded
 */
window.AppPageLifecycle.onPageLoad(() => {
  const table = document.getElementById('supplier-catalog-formset');
  const addButton = document.getElementById('add-material-row');
  const totalForms = document.getElementById('id_catalogo-TOTAL_FORMS');

  if (!table || !addButton || !totalForms) return;

  const tbody = table.querySelector('tbody');
  const form = table.closest('form');
  const priceError = 'No se permiten precios negativos. Ingresa un valor mayor que cero.';

  function clearPriceError(field) {
    field.setCustomValidity('');
  }

  function showPriceError(field) {
    field.setCustomValidity(priceError);
    field.reportValidity();
  }

  tbody.addEventListener('paste', (event) => {
    const field = event.target.closest('input[name$="-precio_actual"]');
    if (!field) return;

    const pastedValue = (event.clipboardData?.getData('text') || '').trim().replace(/[−–]/g, '-');
    if (pastedValue.startsWith('-')) {
      event.preventDefault();
      showPriceError(field);
      window.setTimeout(() => clearPriceError(field), 2500);
    }
  });

  tbody.addEventListener('input', (event) => {
    const field = event.target.closest('input[name$="-precio_actual"]');
    if (!field) return;

    if (field.valueAsNumber < 0) {
      field.value = '';
      showPriceError(field);
      return;
    }
    clearPriceError(field);
  });

  form?.addEventListener('submit', (event) => {
    const negativePrice = Array.from(tbody.querySelectorAll('input[name$="-precio_actual"]'))
      .find((field) => field.value !== '' && field.valueAsNumber < 0);
    if (negativePrice) {
      event.preventDefault();
      showPriceError(negativePrice);
    }
  });

  /**
   * Actualiza los contadores de fila después de agregar o eliminar
   */
  function refreshCounters() {
    tbody.querySelectorAll('.supplier-formset-row:not(.d-none)').forEach((row, index) => {
      const counter = row.querySelector('.supplier-row-count');
      if (counter) counter.textContent = index + 1;
    });
  }

  function refreshRowStock(row) {
    const select = row.querySelector('select[name$="-material"]');
    const stockCell = row.querySelector('.supplier-stock-current');
    if (!select || !stockCell) return;

    const selectedOption = select.selectedOptions[0];
    const stock = Number(selectedOption?.dataset.stock ?? 0);
    stockCell.dataset.currentStock = String(stock);
    stockCell.dataset.unit = selectedOption?.dataset.unit || 'unidades';
    const stockValue = stockCell.querySelector('.supplier-stock-value');
    if (stockValue) stockValue.textContent = new Intl.NumberFormat('es-CO').format(stock);

    refreshStockPreview(row);
  }

  function refreshStockPreview(row) {
    const stockCell = row.querySelector('.supplier-stock-current');
    const quantityField = row.querySelector('input[name$="-cantidad_recibida"]');
    const preview = row.querySelector('.supplier-stock-preview');
    if (!stockCell || !quantityField || !preview) return;

    const currentStock = Number(stockCell.dataset.currentStock || 0);
    const unit = stockCell.dataset.unit || 'unidades';
    const quantityReceived = Number(quantityField.value);
    if (!Number.isInteger(quantityReceived) || quantityReceived <= 0) {
      preview.textContent = '';
      return;
    }

    const resultingStock = currentStock + quantityReceived;
    preview.textContent = `Al registrar: ${new Intl.NumberFormat('es-CO').format(resultingStock)} ${unit} en inventario`;
  }

  tbody.querySelectorAll('.supplier-formset-row').forEach((row) => {
    refreshRowStock(row);
    row.querySelector('input[name$="-cantidad_recibida"]')?.addEventListener('input', () => {
      refreshStockPreview(row);
    });
  });

  tbody.addEventListener('change', (event) => {
    const select = event.target.closest('select[name$="-material"]');
    if (select) refreshRowStock(select.closest('.supplier-formset-row'));
    const quantity = event.target.closest('input[name$="-cantidad_recibida"]');
    if (quantity) refreshStockPreview(quantity.closest('.supplier-formset-row'));
  });

  addButton.addEventListener('click', () => {
    const firstRow = tbody.querySelector('.supplier-formset-row');
    if (!firstRow) return;

    const formCount = Number(totalForms.value);
    const newRow = firstRow.cloneNode(true);

    newRow.querySelectorAll('input, select, textarea').forEach((field) => {
      if (!field.name) return;
      field.name = field.name.replace(/-\d+-/, `-${formCount}-`);
      field.id = field.id.replace(/-\d+-/, `-${formCount}-`);

      if (field.type === 'checkbox') {
        field.checked = !field.name.endsWith('-DELETE');
      } else if (field.type === 'hidden' && field.name.endsWith('-id')) {
        field.value = '';
      } else if (field.type !== 'hidden') {
        field.value = '';
      }
    });

    newRow.classList.remove('d-none');
    refreshRowStock(newRow);
    newRow.querySelector('input[name$="-cantidad_recibida"]')?.addEventListener('input', () => {
      refreshStockPreview(newRow);
    });
    tbody.appendChild(newRow);
    totalForms.value = formCount + 1;
    refreshCounters();
  });

  tbody.addEventListener('click', (event) => {
    const button = event.target.closest('.supplier-remove-row');
    if (!button) return;

    const row = button.closest('.supplier-formset-row');
    const deleteInput = row.querySelector('input[name$="-DELETE"]');

    if (deleteInput) {
      deleteInput.checked = true;
      row.classList.add('d-none');
    } else {
      row.remove();
    }

    refreshCounters();
  });
});
