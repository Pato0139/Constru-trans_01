/**
 * @file Gestión del formulario de catálogo de materiales de proveedores
 */

/**
 * Inicializa el formset de catálogo de proveedores
 * @listens DOMContentLoaded
 */
document.addEventListener('DOMContentLoaded', () => {
  const table = document.getElementById('supplier-catalog-formset');
  const addButton = document.getElementById('add-material-row');
  const totalForms = document.getElementById('id_catalogo-TOTAL_FORMS');

  if (!table || !addButton || !totalForms) return;

  const tbody = table.querySelector('tbody');

  /**
   * Actualiza los contadores de fila después de agregar o eliminar
   */
  function refreshCounters() {
    tbody.querySelectorAll('.supplier-formset-row:not(.d-none)').forEach((row, index) => {
      const counter = row.querySelector('.supplier-row-count');
      if (counter) counter.textContent = index + 1;
    });
  }

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
      } else if (field.type !== 'hidden') {
        field.value = '';
      }
    });

    newRow.classList.remove('d-none');
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
