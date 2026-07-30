/**
 * Turns numeric quantity inputs into accessible minus/value/plus controls.
 */
document.addEventListener('DOMContentLoaded', () => {
  const clampQuantity = (input) => {
    const stepper = input.closest('.quantity-stepper');
    const min = parseFloat(input.getAttribute('min') || stepper?.dataset.min || 1);
    const maxAttr = input.getAttribute('max') || stepper?.dataset.max;
    const max = maxAttr ? parseFloat(maxAttr) : null;
    const step = parseFloat(input.getAttribute('step') || stepper?.dataset.step || 1);
    let value = parseFloat(input.value || min);

    if (Number.isNaN(value) || value < min) value = min;
    if (max !== null && value > max) value = max;

    input.value = Number.isInteger(step) ? String(Math.round(value)) : value.toFixed(2).replace(/\.?0+$/, '');
    return value;
  };

  const adjustQuantity = (button, delta) => {
    const stepper = button.closest('.quantity-stepper');
    const input = stepper?.querySelector('input[type="number"]');
    if (!input) return;

    const current = clampQuantity(input);
    const step = parseFloat(input.getAttribute('step') || stepper?.dataset.step || 1);
    input.value = current + (delta * step);
    clampQuantity(input);
    input.dispatchEvent(new Event('input', { bubbles: true }));
    input.dispatchEvent(new Event('change', { bubbles: true }));
  };

  document.querySelectorAll('.quantity-stepper__input').forEach((input) => {
    clampQuantity(input);
    input.addEventListener('change', () => clampQuantity(input));
    input.addEventListener('blur', () => clampQuantity(input));
  });

  document.addEventListener('click', (event) => {
    const minus = event.target.closest('.quantity-stepper__btn--minus');
    const plus = event.target.closest('.quantity-stepper__btn--plus');

    if (minus) adjustQuantity(minus, -1);
    if (plus) adjustQuantity(plus, 1);
  });
});
