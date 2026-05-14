document.addEventListener("DOMContentLoaded", function() {
    const loader = document.getElementById("loader-container");
    const body = document.body;

    if (!loader) return;

    // Bloquear scroll mientras el loader está activo
    body.style.overflow = "hidden";

    function hideLoader() {
        if (!loader.classList.contains("fade-out")) {
            // Forzar que la barra llegue al 100% al ocultar
            const progressBar = loader.querySelector(".progress-bar");
            if (progressBar) {
                progressBar.style.width = "100%";
                progressBar.style.transition = "width 0.3s ease-out";
            }

            setTimeout(() => {
                loader.classList.add("fade-out");
                // Rehabilitar scroll
                body.style.overflow = "";

                setTimeout(() => {
                    loader.style.display = "none";
                }, 300); // Esperar a que termine la transición de opacidad
            }, 100); // Pequeña pausa para ver la barra al 100%
        }
    }

    // Ocultar cuando la página esté completamente cargada
    if (document.readyState === "complete") {
        setTimeout(hideLoader, 100);
    } else {
        window.addEventListener("load", function() {
            setTimeout(hideLoader, 100);
        });
    }

    // Timeout de seguridad por si tarda demasiado en cargar
    setTimeout(hideLoader, 1500);

    // Mostrar loader al enviar formularios (excluyendo los que se manejen por AJAX si los hay)
    const forms = document.querySelectorAll("form");
    forms.forEach((form) => {
        form.addEventListener("submit", function() {
            // No mostrar si el formulario tiene errores de validación nativos
            if (form.checkValidity()) {
                // Bloquear scroll
                body.style.overflow = "hidden";

                // Reiniciar barra de progreso para la nueva acción
                const progressBar = loader.querySelector(".progress-bar");
                if (progressBar) {
                    progressBar.style.transition = "none";
                    progressBar.style.width = "0%";
                    void progressBar.offsetWidth; // Force reflow
                    progressBar.style.transition = "";
                }

                loader.style.display = "flex";
                loader.classList.remove("fade-out");
                loader.style.opacity = "1";
                loader.style.pointerEvents = "auto";
            }
        });
    });
});