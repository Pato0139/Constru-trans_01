/**
 * Initializes Bootstrap tooltips for action controls across the project.
 *
 * Buttons and links that already expose a title, aria-label, data-tooltip, or
 * visible text receive a consistent tooltip without requiring every template to
 * duplicate Bootstrap attributes by hand.
 */
document.addEventListener('DOMContentLoaded', () => {
  if (!window.bootstrap || !bootstrap.Tooltip) return;

  const inferTooltipLabel = (element) => {
    const classList = element.classList;
    const icon = element.querySelector('i');
    const iconClass = icon ? icon.className : '';
    const href = element.getAttribute('href') || '';

    if (classList.contains('chat-widget-toggle')) return 'Abrir asistente virtual';
    if (classList.contains('chat-widget-close') || classList.contains('btn-close')) return 'Cerrar';
    if (classList.contains('chat-widget-send')) return 'Enviar mensaje';
    if (classList.contains('confirm-delete-form')) return 'Eliminar registro';
    if (classList.contains('btn-eliminar-material')) return 'Eliminar material';
    if (classList.contains('remove-form-row') || classList.contains('btn-eliminar-fila')) return 'Eliminar fila';
    if (element.id === 'btn-agregar-material') return 'Agregar material';
    if (element.id === 'btn-fecha-entrega') return 'Seleccionar fecha de entrega';
    if (href.includes('crear') || iconClass.includes('bi-plus')) return 'Crear registro';
    if (href.includes('detalle') || iconClass.includes('bi-eye')) return 'Ver detalle';
    if (iconClass.includes('bi-pencil')) return 'Editar';
    if (iconClass.includes('bi-trash')) return 'Eliminar';
    if (iconClass.includes('bi-calendar')) return 'Seleccionar fecha';
    if (iconClass.includes('bi-arrow-left')) return 'Volver';
    if (element.type === 'submit') return 'Enviar formulario';

    return '';
  };

  const actionSelector = [
    'button',
    'a.btn',
    '[role="button"]',
    '.dropdown-item',
    '.navbar-icon-btn',
    '.bd-mode-switch',
  ].join(',');

  document.querySelectorAll(actionSelector).forEach((element) => {
    if (element.disabled || element.closest('[data-tooltip-disabled="true"]')) return;

    const label = (
      element.dataset.tooltip
      || element.getAttribute('aria-label')
      || element.getAttribute('title')
      || element.textContent
      || inferTooltipLabel(element)
      || ''
    ).trim().replace(/\s+/g, ' ');

    if (!label) return;

    if (!element.getAttribute('aria-label')) {
      element.setAttribute('aria-label', label);
    }
    element.setAttribute('data-bs-title', label);
    element.setAttribute('data-bs-placement', element.dataset.bsPlacement || 'bottom');

    new bootstrap.Tooltip(element, {
      container: 'body',
      trigger: 'hover focus',
    });
  });
});
