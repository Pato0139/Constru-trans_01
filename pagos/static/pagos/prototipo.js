document.addEventListener('DOMContentLoaded', function () {
  const addMaterialButton = document.getElementById('add-material');
  const materialsBody = document.getElementById('materials-body');
  const materialsJson = document.getElementById('materials-json');
  const proofInput = document.getElementById('proof-input');
  const previewBox = document.getElementById('preview-box');
  const previewLabel = document.getElementById('preview-label');
  const previewName = document.getElementById('preview-name');
  const previewSize = document.getElementById('preview-size');
  const proofText = document.getElementById('proof-text');

  if (addMaterialButton && materialsBody) {
    addMaterialButton.addEventListener('click', function () {
      const row = document.createElement('div');
      row.className = 'material-row';
      row.innerHTML = `
        <div>
          <label class="form-label small text-muted">Material</label>
          <select class="form-select form-select-sm" name="material_name">
            <option value="Cemento">Cemento</option>
            <option value="Arena">Arena</option>
            <option value="Varilla">Varilla</option>
            <option value="Bloques">Bloques</option>
          </select>
        </div>
        <div>
          <label class="form-label small text-muted">Cantidad</label>
          <input type="number" class="form-control form-control-sm" name="material_quantity" min="1" value="1">
        </div>
        <div>
          <label class="form-label small text-muted">Unidad</label>
          <input type="text" class="form-control form-control-sm" name="material_unit" value="sacos">
        </div>
        <div>
          <label class="form-label small text-muted">&nbsp;</label>
          <button type="button" class="btn btn-outline-danger btn-sm remove-row">Quitar</button>
        </div>`;
      materialsBody.appendChild(row);
      row.querySelector('.remove-row').addEventListener('click', function () {
        row.remove();
        syncMaterialsJson();
      });
      syncMaterialsJson();
    });

    document.querySelectorAll('.remove-row').forEach(function (button) {
      button.addEventListener('click', function () {
        button.closest('.material-row').remove();
        syncMaterialsJson();
      });
    });
  }

  function syncMaterialsJson() {
    if (!materialsJson) return;
    const rows = Array.from(materialsBody.querySelectorAll('.material-row'));
    const payload = rows.map(function (row) {
      const name = row.querySelector('[name="material_name"]').value;
      const quantity = row.querySelector('[name="material_quantity"]').value;
      const unit = row.querySelector('[name="material_unit"]').value;
      return {
        name: name,
        quantity: quantity,
        unit: unit,
        unit_price: {
          Cemento: 45000,
          Arena: 22000,
          Varilla: 120000,
          Bloques: 1800
        }[name] || 50000
      };
    });
    materialsJson.value = JSON.stringify(payload);
    updateSummary(payload);
  }

  function updateSummary(payload) {
    const subtotalEl = document.getElementById('summary-subtotal');
    const ivaEl = document.getElementById('summary-iva');
    const totalEl = document.getElementById('summary-total');
    if (!subtotalEl || !ivaEl || !totalEl) return;

    const subtotal = payload.reduce(function (acc, item) {
      return acc + (Number(item.quantity) || 0) * Number(item.unit_price || 0);
    }, 0);
    const iva = Math.round(subtotal * 0.19);
    const total = subtotal + iva;

    subtotalEl.textContent = '$' + subtotal.toLocaleString('es-CO');
    ivaEl.textContent = '$' + iva.toLocaleString('es-CO');
    totalEl.textContent = '$' + total.toLocaleString('es-CO');
  }

  if (materialsBody) {
    materialsBody.addEventListener('input', syncMaterialsJson);
    materialsBody.addEventListener('change', syncMaterialsJson);
    syncMaterialsJson();
  }

  if (proofInput && previewBox) {
    proofInput.addEventListener('change', function () {
      const file = this.files && this.files[0];
      if (!file) {
        previewBox.innerHTML = '<div class="text-center"><i class="bi bi-cloud-arrow-up fs-1"></i><p class="mb-0 mt-2">Vista previa del comprobante</p></div>';
        previewLabel.textContent = 'Vista previa';
        previewName.textContent = '';
        previewSize.textContent = '';
        proofText.textContent = 'Aún no se ha adjuntado ningún archivo.';
        return;
      }

      if (file.type.startsWith('image/')) {
        const reader = new FileReader();
        reader.onload = function (event) {
          previewBox.innerHTML = '<img class="preview-img" src="' + event.target.result + '" alt="Preview">';
        };
        reader.readAsDataURL(file);
      } else {
        previewBox.innerHTML = '<div class="text-center"><i class="bi bi-file-earmark-pdf fs-1"></i><p class="mb-0 mt-2">Documento listo para enviar</p></div>';
      }

      previewLabel.textContent = 'Archivo listo';
      previewName.textContent = file.name;
      previewSize.textContent = (file.size / (1024 * 1024)).toFixed(2) + ' MB';
      proofText.textContent = 'Se adjuntó el comprobante para revisión.';
    });
  }

  document.querySelectorAll('[data-copy]').forEach(function (button) {
    button.addEventListener('click', function () {
      const target = this.dataset.copy;
      navigator.clipboard.writeText(target).then(function () {
        const oldText = button.textContent;
        button.textContent = '¡Copiado!';
        setTimeout(function () { button.textContent = oldText; }, 1200);
      });
    });
  });
});
