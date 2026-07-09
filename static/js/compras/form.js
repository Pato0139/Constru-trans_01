document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('compra-form');
  const providerSelect = document.getElementById('id_proveedor');
  const catalogUrlInput = document.getElementById('supplier-catalog-url');
  const tableBody = document.querySelector('#detalles-table tbody');
  const totalForms = document.getElementById('id_detalles-TOTAL_FORMS');
  const addButton = document.getElementById('add-form-row');
  const loader = document.getElementById('catalog-loader');
  const hint = document.getElementById('catalog-hint');

  if (!form || !providerSelect || !catalogUrlInput || !tableBody || !totalForms || !addButton) return;

  let catalog = [];
  const taxRate = Number(window.purchaseTaxRate || 0);

  function formatCurrency(value) {
    return Number(value || 0).toLocaleString('es-CO', {
      style: 'currency',
      currency: 'COP',
      minimumFractionDigits: 2,
    });
  }

  function getCatalogUrl(providerId) {
    return catalogUrlInput.value.replace('/0/', `/${providerId}/`);
  }

  function setLoading(isLoading) {
    if (loader) loader.classList.toggle('is-visible', isLoading);
  }

  function materialOptions(selectedValue = '') {
    const options = ['<option value="">Seleccionar material...</option>'];
    catalog.forEach((item) => {
      const selected = String(item.id) === String(selectedValue) ? 'selected' : '';
      options.push(`<option value="${item.id}" ${selected}>${item.nombre}</option>`);
    });
    return options.join('');
  }

  function rowFields(row) {
    return {
      material: row.querySelector('.material-select'),
      quantity: row.querySelector('.cantidad-input'),
      price: row.querySelector('.precio-input'),
      unit: row.querySelector('.unit-cell'),
      updated: row.querySelector('.updated-cell'),
      subtotal: row.querySelector('.subtotal-cell'),
    };
  }

  function applyMaterialData(row) {
    const fields = rowFields(row);
    const item = catalog.find((entry) => String(entry.id) === String(fields.material.value));

    if (!item) {
      fields.unit.textContent = '-';
      fields.updated.textContent = '-';
      fields.price.value = '';
      updateCalculations();
      return;
    }

    fields.unit.textContent = item.unidad || '-';
    fields.updated.textContent = item.fecha_actualizacion || '-';
    fields.price.value = item.precio;
    updateCalculations();
  }

  function updateCalculations() {
    let subtotal = 0;
    let count = 0;

    tableBody.querySelectorAll('.formset-row:not(.d-none)').forEach((row) => {
      const fields = rowFields(row);
      const quantity = Number(fields.quantity.value || 0);
      const price = Number(fields.price.value || 0);
      const lineSubtotal = quantity * price;

      fields.subtotal.textContent = formatCurrency(lineSubtotal);
      subtotal += lineSubtotal;

      if (fields.material.value && quantity > 0) count += 1;
    });

    const taxes = subtotal * taxRate;
    document.getElementById('subtotal-order').textContent = formatCurrency(subtotal);
    document.getElementById('tax-order').textContent = formatCurrency(taxes);
    document.getElementById('total-order').textContent = formatCurrency(subtotal + taxes);
    document.getElementById('material-count').textContent = count;
  }

  function prepareRow(row) {
    const fields = rowFields(row);
    const selected = fields.material.value;

    fields.material.innerHTML = materialOptions(selected);
    fields.price.readOnly = true;

    fields.material.addEventListener('change', () => applyMaterialData(row));
    fields.quantity.addEventListener('input', updateCalculations);
    applyMaterialData(row);
  }

  async function loadCatalog() {
    const providerId = providerSelect.value;
    catalog = [];

    tableBody.querySelectorAll('.formset-row').forEach((row) => {
      const fields = rowFields(row);
      fields.material.innerHTML = '<option value="">Seleccionar proveedor primero...</option>';
      fields.price.value = '';
      fields.unit.textContent = '-';
      fields.updated.textContent = '-';
    });

    if (!providerId) {
      if (hint) hint.textContent = 'Selecciona un proveedor para cargar únicamente los materiales que vende.';
      updateCalculations();
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(getCatalogUrl(providerId), {
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
      });
      const data = await response.json();
      catalog = data.materiales || [];

      if (hint) {
        hint.textContent = catalog.length
          ? `${data.proveedor.nombre}: ${catalog.length} materiales disponibles.`
          : 'Este proveedor no tiene materiales activos registrados.';
      }

      tableBody.querySelectorAll('.formset-row:not(.d-none)').forEach(prepareRow);
    } catch (error) {
      if (hint) hint.textContent = 'No se pudo cargar el catálogo del proveedor.';
    } finally {
      setLoading(false);
      updateCalculations();
    }
  }

  function addRow() {
    const firstRow = tableBody.querySelector('.formset-row');
    if (!firstRow) return;

    const formCount = Number(totalForms.value);
    const newRow = firstRow.cloneNode(true);

    newRow.querySelectorAll('input, select').forEach((field) => {
      if (!field.name) return;
      field.name = field.name.replace(/-\d+-/, `-${formCount}-`);
      field.id = field.id.replace(/-\d+-/, `-${formCount}-`);

      if (field.type === 'checkbox') {
        field.checked = false;
      } else if (field.type !== 'hidden') {
        field.value = '';
      }
    });

    newRow.classList.remove('d-none');
    newRow.querySelector('.counter').textContent = formCount + 1;
    tableBody.appendChild(newRow);
    totalForms.value = formCount + 1;
    prepareRow(newRow);
    updateCalculations();
  }

  providerSelect.addEventListener('change', loadCatalog);
  addButton.addEventListener('click', addRow);

  tableBody.addEventListener('click', (event) => {
    const button = event.target.closest('.remove-form-row');
    if (!button) return;

    const row = button.closest('.formset-row');
    const deleteInput = row.querySelector('input[name$="-DELETE"]');

    if (deleteInput) {
      deleteInput.checked = true;
      row.classList.add('d-none');
    } else {
      row.remove();
    }

    updateCalculations();
  });

  loadCatalog();
});
