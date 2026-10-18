/**
 * tooltips.js
 * 
 * Gestión inteligente y limpia de tooltips con Bootstrap 5:
 * 1. Solo aplica tooltips a elementos que los necesitan (botones de solo ícono o con tooltip explícito).
 * 2. NO duplica tooltips en botones que ya tienen texto legible (evita "Revisar pago", "Volver a Pagos", etc.).
 * 3. Utiliza únicamente el disparador 'hover' (NUNCA 'focus' permanente al hacer clic).
 * 4. Limpia instantáneamente tooltips huérfanos al hacer clic, al navegar o al hacer scroll.
 */

(function (global) {
  'use strict';

  /**
   * Elimina del DOM cualquier contenedor de tooltip flotante o huérfano.
   */
  function cleanupOrphanTooltips() {
    document.querySelectorAll('.tooltip').forEach((tip) => {
      tip.remove();
    });
  }

  global.cleanupOrphanTooltips = cleanupOrphanTooltips;

  /**
   * Deduce una etiqueta descriptiva únicamente para botones de SOLO ícono.
   */
  function inferIconTooltipLabel(element) {
    const classList = element.classList;
    const icon = element.querySelector('i');
    const iconClass = icon ? icon.className : '';
    const href = element.getAttribute('href') || '';

    if (classList.contains('chat-widget-toggle')) return 'Abrir asistente virtual';
    if (classList.contains('chat-widget-close') || classList.contains('btn-close')) return 'Cerrar';
    if (classList.contains('chat-widget-send')) return 'Enviar mensaje';
    if (classList.contains('confirm-delete-form') || classList.contains('btn-eliminar-material')) return 'Eliminar registro';
    if (classList.contains('remove-form-row') || classList.contains('btn-eliminar-fila')) return 'Eliminar fila';
    if (element.id === 'btn-agregar-material') return 'Agregar material';
    if (element.id === 'btn-fecha-entrega') return 'Seleccionar fecha de entrega';
    if (href.includes('crear') || iconClass.includes('bi-plus')) return 'Crear registro';
    if (href.includes('detalle') || iconClass.includes('bi-eye')) return 'Ver detalle';
    if (iconClass.includes('bi-pencil')) return 'Editar';
    if (iconClass.includes('bi-trash')) return 'Eliminar';
    if (iconClass.includes('bi-calendar')) return 'Seleccionar fecha';
    if (iconClass.includes('bi-arrow-left')) return 'Volver';

    return '';
  }

  /**
   * Inicializa tooltips de forma segura y controlada en la página.
   */
  function initAppTooltips() {
    if (!global.bootstrap || !global.bootstrap.Tooltip) return;

    // Limpiar restos huérfanos previos
    cleanupOrphanTooltips();

    const actionSelector = [
      'button',
      'a.btn',
      'a.btn-action',
      '[role="button"]',
      '.dropdown-item',
      '.navbar-icon-btn',
      '.bd-mode-switch',
      '[data-bs-toggle="tooltip"]',
      '[data-tooltip]',
    ].join(',');

    document.querySelectorAll(actionSelector).forEach((element) => {
      if (element.disabled || element.closest('[data-tooltip-disabled="true"]')) return;

      // Destruir cualquier instancia previa para evitar duplicados
      const existingInstance = global.bootstrap.Tooltip.getInstance(element);
      if (existingInstance) {
        try { existingInstance.dispose(); } catch (_) {}
      }

      // Si tiene atributo title nativo, transferirlo a data-bs-title y remover title para evitar doble tooltip
      const rawTitle = element.getAttribute('title');
      if (rawTitle) {
        element.setAttribute('data-bs-title', rawTitle);
        element.removeAttribute('title');
      }

      const explicitTooltip = element.dataset.tooltip || element.getAttribute('data-bs-title');
      const visibleText = (element.innerText || '').trim();

      // Si el botón ya tiene texto visible y NO tiene un tooltip explícito configurado a propósito,
      // NO generamos tooltip redundante (evita que diga "Revisar pago" encima del texto "Revisar pago").
      if (visibleText.length > 0 && !explicitTooltip) {
        return;
      }

      // Obtener o inferir etiqueta
      const label = (
        explicitTooltip
        || element.getAttribute('aria-label')
        || inferIconTooltipLabel(element)
        || ''
      ).trim().replace(/\s+/g, ' ');

      if (!label) return;

      // Configurar atributos requeridos
      if (!element.getAttribute('aria-label')) {
        element.setAttribute('aria-label', label);
      }
      element.setAttribute('data-bs-title', label);
      element.setAttribute('data-bs-placement', element.dataset.bsPlacement || 'bottom');

      try {
        const tooltipInstance = new global.bootstrap.Tooltip(element, {
          container: 'body',
          trigger: 'hover', // ÚNICAMENTE hover. Nunca 'focus' para evitar que se quede pegado al hacer clic.
          delay: { show: 200, hide: 50 },
          animation: true,
        });

        // Al hacer clic, ocultar inmediatamente el tooltip para que no quede flotando
        element.addEventListener('click', () => {
          try { tooltipInstance.hide(); } catch (_) {}
          cleanupOrphanTooltips();
        }, { passive: true });

        // Al salir el cursor o perder foco, garantizar ocultación
        element.addEventListener('mouseleave', () => {
          try { tooltipInstance.hide(); } catch (_) {}
        }, { passive: true });

        element.addEventListener('blur', () => {
          try { tooltipInstance.hide(); } catch (_) {}
        }, { passive: true });

      } catch (err) {
        console.warn('No se pudo inicializar el tooltip en el elemento:', element, err);
      }
    });
  }

  global.initAppTooltips = initAppTooltips;

  // Limpieza global ante cualquier clic, scroll o Escape
  document.addEventListener('pointerdown', (e) => {
    // Si el clic no fue dentro del tooltip mismo, eliminar cualquier tooltip flotante
    if (!e.target.closest('.tooltip')) {
      cleanupOrphanTooltips();
    }
  }, { passive: true });

  window.addEventListener('scroll', () => {
    cleanupOrphanTooltips();
  }, { passive: true });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      cleanupOrphanTooltips();
    }
  }, { passive: true });

  // Integración con el ciclo de vida de la aplicación
  if (global.AppPageLifecycle && typeof global.AppPageLifecycle.onPageLoad === 'function') {
    global.AppPageLifecycle.onPageLoad(initAppTooltips);
  } else {
    document.addEventListener('DOMContentLoaded', initAppTooltips);
  }

  document.addEventListener('app:page-loaded', initAppTooltips);

})(window);
