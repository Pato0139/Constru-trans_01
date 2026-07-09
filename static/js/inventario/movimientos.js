document.addEventListener('DOMContentLoaded', () => {
  const modalElement = document.getElementById('modalEntrada');
  const form = document.getElementById('formEntrada');

  if (!modalElement || !form) return;

  if (modalElement.parentElement !== document.body) {
    document.body.appendChild(modalElement);
  }

  const modal = window.bootstrap ? bootstrap.Modal.getOrCreateInstance(modalElement) : null;
  const submitButton = form.querySelector('button[type="submit"]');
  const originalSubmitText = submitButton ? submitButton.innerHTML : '';

  function showMessage(type, message) {
    if (window.Swal) {
      Swal.fire({
        icon: type,
        title: type === 'success' ? 'Entrada registrada' : 'No se pudo registrar',
        text: message,
        timer: type === 'success' ? 1600 : undefined,
        showConfirmButton: type !== 'success',
      });
      return;
    }

    window.alert(message);
  }

  modalElement.addEventListener('shown.bs.modal', () => {
    const firstControl = form.querySelector('select, input, textarea, button');
    if (firstControl) firstControl.focus();
  });

  modalElement.addEventListener('hidden.bs.modal', () => {
    form.reset();
    const quantity = form.querySelector('input[name="cantidad"]');
    if (quantity) quantity.value = '1';
  });

  form.addEventListener('submit', async (event) => {
    event.preventDefault();

    if (!form.reportValidity()) return;

    const endpoint = window.urlRegistrarEntrada;
    if (!endpoint) {
      showMessage('error', 'No se encontró la ruta para registrar la entrada.');
      return;
    }

    if (submitButton) {
      submitButton.disabled = true;
      submitButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2" aria-hidden="true"></span>Guardando...';
    }

    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        body: new FormData(form),
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
        },
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok || data.error) {
        throw new Error(data.error || 'Revisa los datos e inténtalo nuevamente.');
      }

      if (modal) modal.hide();
      showMessage('success', 'El stock se actualizó correctamente.');
      window.setTimeout(() => window.location.reload(), 900);
    } catch (error) {
      showMessage('error', error.message || 'Ocurrió un error al registrar la entrada.');
    } finally {
      if (submitButton) {
        submitButton.disabled = false;
        submitButton.innerHTML = originalSubmitText;
      }
    }
  });
});
