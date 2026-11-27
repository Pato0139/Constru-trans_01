(() => {
  const init = () => {
    const form = document.getElementById('purchase-entry-form');
    const rows = document.getElementById('entry-lines');
    const template = document.getElementById('empty-entry-line');
    if (!form || !rows || !template || form.dataset.bound === '1') return;
    form.dataset.bound = '1';
    form.querySelector('[name="proveedor"]')?.addEventListener('change', event => {
      const url = new URL(window.location.href);
      url.searchParams.set('proveedor', event.target.value);
      window.location.assign(url);
    });
    rows.addEventListener('change', event => {
      if (!event.target.matches('.material-select')) return;
      const row = event.target.closest('[data-entry-line]');
      row.querySelector('.sale-price').value = event.target.selectedOptions[0]?.dataset.precio || '';
      row.querySelector('.update-sale-price').checked = false;
    });
    const totalForms = form.querySelector('[name="detalles-TOTAL_FORMS"]');
    const money = value => new Intl.NumberFormat('es-CO', {style:'currency',currency:'COP',maximumFractionDigits:2}).format(value || 0);
    const recalc = row => {
      const select = row.querySelector('.material-select');
      const option = select?.selectedOptions?.[0];
      const stock = Number(option?.dataset.stock || 0);
      const unit = option?.dataset.unit || 'unidad';
      const quantity = Number(row.querySelector('.quantity-input')?.value || 0);
      const price = Number(row.querySelector('.purchase-price')?.value || 0);
      const stockLabel = row.querySelector('[data-stock-label]');
      const unitLabel = row.querySelector('[data-unit-label]');
      const subtotal = row.querySelector('[data-subtotal]');
      const result = row.querySelector('[data-stock-result]');
      if (stockLabel) stockLabel.textContent = `${new Intl.NumberFormat('es-CO').format(stock)} ${unit}`;
      if (unitLabel) unitLabel.textContent = unit;
      if (subtotal) subtotal.textContent = money(quantity * price);
      if (result) result.textContent = option?.value ? `Stock final: ${new Intl.NumberFormat('es-CO').format(stock + quantity)} ${unit}` : 'Stock final: —';
      const saleField = row.querySelector('.sale-price');
      const updateSale = row.querySelector('.update-sale-price');
      if (saleField && option?.value && !saleField.value) saleField.value = option.dataset.precio || '';
      if (saleField) saleField.disabled = !updateSale?.checked;
    };
    const updateTotal = () => {
      let total = 0;
      rows.querySelectorAll('[data-entry-line]:not([hidden])').forEach(row => {
        const q = Number(row.querySelector('.quantity-input')?.value || 0);
        const p = Number(row.querySelector('.purchase-price')?.value || 0);
        total += q * p;
        recalc(row);
      });
      const totalLabel = document.getElementById('entry-total');
      if (totalLabel) totalLabel.textContent = money(total);
    };
    rows.addEventListener('input', updateTotal);
    rows.addEventListener('change', updateTotal);
    rows.addEventListener('click', event => {
      const button = event.target.closest('.remove-entry-material');
      if (!button) return;
      const row = button.closest('[data-entry-line]');
      const deleteBox = row?.querySelector('[name$="-DELETE"]');
      if (deleteBox) deleteBox.checked = true;
      if (row) row.hidden = true;
      updateTotal();
    });
    document.getElementById('add-entry-material')?.addEventListener('click', () => {
      const index = Number(totalForms.value);
      rows.insertAdjacentHTML('beforeend', template.innerHTML.replaceAll('__prefix__', index));
      totalForms.value = index + 1;
      updateTotal();
    });
    form.addEventListener('submit', event => {
      const button = document.getElementById('confirm-entry');
      if (button?.dataset.confirmed === '1') {
        if (button.dataset.submitting === '1') { event.preventDefault(); return; }
        button.dataset.submitting = '1';
        button.disabled = true;
        button.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Guardando entrada…';
        return;
      }
      event.preventDefault();
      const count = Array.from(rows.querySelectorAll('[data-entry-line]:not([hidden]) .material-select'))
        .filter(select => select.value).length;
      const amount = document.getElementById('entry-total')?.textContent || '$0';
      const proceed = () => {
        if (!button) return;
        button.dataset.confirmed = '1';
        form.requestSubmit(button);
      };
      if (window.Swal?.fire) {
        window.Swal.fire({
          title: '¿Confirmar entrada de materiales?',
          html: `<p>Se registrarán <strong>${count}</strong> materiales por un total de <strong>${amount}</strong>.</p><p>El inventario se actualizará al confirmar.</p>`,
          icon: 'question',
          showCancelButton: true,
          confirmButtonText: 'Confirmar entrada',
          cancelButtonText: 'Revisar datos',
          reverseButtons: true,
          customClass: {popup: 'ct-alert-popup', confirmButton: 'btn btn-warning', cancelButton: 'btn btn-outline-light'},
          buttonsStyling: false,
        }).then(result => { if (result.isConfirmed) proceed(); });
      } else if (window.confirm(`¿Confirmas la entrada de ${count} materiales por ${amount}?`)) {
        proceed();
      }
    });
    updateTotal();
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, {once:true}); else init();
  document.addEventListener('app:page-loaded', init);
})();
