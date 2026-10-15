#!/usr/bin/env python3
# Write the improved ayuda.html template
content = r'''{% extends "base.html" %}

{% block title %}Centro de Ayuda - Constru-trans{% endblock %}

{% block extra_css %}
<style>
  .help-page {
    background: #0f1115;
  }
  .help-page .home-section {
    background: linear-gradient(135deg, #1a1d24 0%, #1f242b 50%, #1a1d24 100%);
  }
  .help-page .home-section .title {
    font-weight: 700;
    letter-spacing: 0.5px;
  }
  .help-page .home-section .subtitle {
    font-size: 0.95rem;
    opacity: 0.7;
  }
  .help-page .accordion {
    border: none;
    border-radius: 12px;
    overflow: hidden;
  }
  .help-page .accordion .accordion-item {
    border-radius: 10px;
    margin-bottom: 12px;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.25);
  }
  .help-page .accordion .accordion-button {
    background: transparent;
    border: none;
    border-radius: 10px;
    padding: 18px 22px;
    color: #e2e8f0;
    font-weight: 600;
    font-size: 1.05rem;
    transition: all 0.2s;
  }
  .help-page .accordion .accordion-button:hover {
    background: rgba(99, 102, 241, 0.15);
    color: #ffffff;
    transform: translateX(4px);
  }
  .help-page .accordion .accordion-button::after {
    content: "\f46a";
    font-family: "Bootstrap Icons";
    font-size: 1.2rem;
    color: #6b7280;
  }
  .help-page .accordion .accordion-button:not(.collapsed) {
    background: rgba(99, 102, 241, 0.2);
    color: #ffffff;
  }
  .help-page .accordion .accordion-button:not(.collapsed)::after {
    content: "\f471";
    color: #818cf8;
  }
  .help-page .accordion .accordion-body {
    padding: 0 22px 22px 22px;
  }
  .help-page .support-card {
    border-radius: 16px;
    border: none;
    background: linear-gradient(135deg, #1e2229 0%, #232833 100%);
    box-shadow: 0 8px 32px rgba(99, 102, 241, 0.15);
  }
  .help-page .support-card .card-body {
    padding: 40px 30px;
    text-align: center;
  }
  .help-page .support-card .support-icon {
    font-size: 2.8rem;
    color: #818cf8;
    margin-bottom: 16px;
  }
  .help-page .support-card h4 {
    font-weight: 700;
    color: #ffffff;
    margin-bottom: 8px;
  }
  .help-page .support-card p {
    color: #9ca3af;
    font-size: 0.95rem;
    margin-bottom: 24px;
  }
  .help-page .support-card .btn-primary {
    background: linear-gradient(135deg, #6366f1, #818cf8);
    border: none;
    border-radius: 50px;
    padding: 12px 32px;
    font-weight: 600;
    font-size: 1.05rem;
    box-shadow: 0 4px 16px rgba(99, 102, 241, 0.35);
    transition: all 0.2s;
  }
  .help-page .support-card .btn-primary:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 24px rgba(99, 102, 241, 0.45);
  }
  .help-page .support-card .btn-outline-light {
    border-radius: 50px;
    border: 2px solid #374151;
    padding: 10px 28px;
    font-weight: 600;
    color: #e5e7eb;
    transition: all 0.2s;
  }
  .help-page .support-card .btn-outline-light:hover {
    border-color: #818cf8;
    color: #818cf8;
  }
  .help-page .scroll-to-top {
    position: fixed;
    bottom: 30px;
    right: 30px;
    width: 48px;
    height: 48px;
    border-radius: 50%;
    background: #6366f1;
    color: #ffffff;
    border: none;
    font-size: 1.4rem;
    cursor: pointer;
    box-shadow: 0 4px 16px rgba(99, 102, 241, 0.4);
    opacity: 0;
    transform: translateY(20px);
    transition: all 0.3s;
    z-index: 1000;
  }
  .help-page .scroll-to-top.visible {
    opacity: 1;
    transform: translateY(0);
  }
  .help-page .scroll-to-top:hover {
    background: #818cf8;
    transform: translateY(-3px);
  }
  .help-page .home-hero {
    padding: 16px 0;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  }
</style>
{% endblock %}

{% block content %}
<div class="help-page">
  <div class="home-hero">
    <div class="container">
      <div class="row align-items-center">
        <div class="col-lg-8">
          <h2 class="text-white title mb-2">
            <i class="bi bi-question-circle-fill me-3 text-primary"></i>
            Centro de Ayuda
          </h2>
          <p class="text-muted subtitle mb-0">
            Guía rápida para el uso del sistema Constru-Trans — todo lo que necesitas saber en un solo lugar
          </p>
        </div>
        <div class="col-lg-4 col-md-6">
          <div class="input-group" style="max-width: 400px;">
            <span class="input-group-text bg-dark border-secondary text-muted">
              <i class="bi bi-search"></i>
            </span>
            <input type="text" class="form-control bg-dark border-secondary text-white"
                   placeholder="Buscar...">
          </div>
        </div>
      </div>
    </div>
  </div>

  <div class="container py-5">
    <div class="row g-4">
      <div class="col-lg-8">
        <div class="accordion help-page" id="helpAccordion">
          <div class="accordion-item">
            <h2 class="accordion-header">
              <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#faq1">
                <i class="bi bi-file-text me-3 text-primary"></i>
                ¿Cómo crear un nuevo pedido?
              </button>
            </h2>
            <div id="faq1" class="accordion-collapse collapse" data-bs-parent="#helpAccordion">
              <div class="accordion-body text-muted">
                Los clientes pueden crear pedidos desde su panel en la sección <strong class="text-white">"Solicitar Pedido"</strong>.
                Deben seleccionar los materiales, la cantidad y confirmar la dirección de entrega.
              </div>
            </div>
          </div>
          <div class="accordion-item">
            <h2 class="accordion-header">
              <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#faq2">
                <i class="bi bi-clock-history me-3 text-primary"></i>
                ¿Cómo realizar el seguimiento de mi entrega?
              </button>
            </h2>
            <div id="faq2" class="accordion-collapse collapse" data-bs-parent="#helpAccordion">
              <div class="accordion-body text-muted">
                En la sección <strong class="text-white">"Seguimiento"</strong>, los clientes pueden ver el estado en tiempo real de sus pedidos:
                Pendiente, En Ruta, Entregado.
              </div>
            </div>
          </div>
          <div class="accordion-item">
            <h2 class="accordion-header">
              <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#faq3">
                <i class="bi bi-download me-3 text-primary"></i>
                ¿Cómo descargar mis facturas?
              </button>
            </h2>
            <div id="faq3" class="accordion-collapse collapse" data-bs-parent="#helpAccordion">
              <div class="accordion-body text-muted">
                Dentro de <strong class="text-white">"Mis Pedidos"</strong>, cada pedido completado tiene un botón de descarga para obtener la
                factura en formato PDF.
              </div>
            </div>
          </div>
          <div class="accordion-item">
            <h2 class="accordion-header">
              <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#faq4">
                <i class="bi bi-credit-card me-3 text-primary"></i>
                ¿Cómo realizar un pago?
              </button>
            </h2>
            <div id="faq4" class="accordion-collapse collapse" data-bs-parent="#helpAccordion">
              <div class="accordion-body text-muted">
                Los pagos se manejan automáticamente al finalizar un pedido. Si necesitas aclarar el método de pago, contacta al soporte técnico.
              </div>
            </div>
          </div>
          <div class="accordion-item">
            <h2 class="accordion-header">
              <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#faq5">
                <i class="bi bi-pin-angle me-3 text-primary"></i>
                ¿Dónde veo mi historial de pedidos?
              </button>
            </h2>
            <div id="faq5" class="accordion-collapse collapse" data-bs-parent="#helpAccordion">
              <div class="accordion-body text-muted">
                En la sección <strong class="text-white">"Mis Pedidos"</strong> puedes ver el historial completo de todos tus pedidos realizados,
                con estado actualizado en tiempo real.
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="col-lg-4">
        <div class="support-card">
          <div class="card-body">
            <div class="support-icon">
              <i class="bi bi-headset"></i>
            </div>
            <h4>Soporte Técnico</h4>
            <p>¿Necesitas ayuda adicional? Estamos aquí para ti.</p>
            <div class="d-grid gap-2 mt-4">
              <a href="mailto:soporte@constru-trans.com" class="btn btn-primary">
                <i class="bi bi-envelope-fill me-2"></i>Enviar Correo
              </a>
              <a href="tel:+573****0000" class="btn btn-outline-light">
                <i class="bi bi-telephone-fill me-2"></i>Llamar Soporte
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <button class="scroll-to-top" id="scrollToTop" aria-label="Volver arriba">
    <i class="bi bi-chevron-up"></i>
  </button>
</div>
{% endblock %}

{% block extra_js %}
<script>
  const scrollToTop = document.getElementById('scrollToTop');
  window.addEventListener('scroll', () => {
    if (window.scrollY > 300) {
      scrollToTop.classList.add('visible');
    } else {
      scrollToTop.classList.remove('visible');
    }
  });
  scrollToTop.addEventListener('click', () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });
</script>
{% endblock %}
'''

with open('/c/Users/edwar/OneDrive/Desktop/Constru-trans_01/templates/ayuda.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("Written: /c/Users/edwar/OneDrive/Desktop/Constru-trans_01/templates/ayuda.html")
