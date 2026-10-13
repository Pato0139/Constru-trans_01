/**
 * Applies dynamic presentation values that come from Django context data.
 *
 * Keeps templates free of inline style attributes while preserving user-specific
 * colors and per-row animation timings.
 */
window.AppPageLifecycle.onPageLoad(() => {
  document.querySelectorAll('[data-bg-color]').forEach((element) => {
    element.style.backgroundColor = element.dataset.bgColor;
  });

  document.querySelectorAll('[data-delay-ms]').forEach((element) => {
    element.style.animationDelay = `${element.dataset.delayMs}ms`;
  });
});
