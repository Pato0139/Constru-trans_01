document.addEventListener("DOMContentLoaded", function() {
    const loader = document.getElementById("loader-container");
    const body = document.body;

    if (!loader) return;

    body.style.overflow = "hidden";

    function hideLoader() {
        if (!loader.classList.contains("fade-out")) {

            const progressBar = loader.querySelector(".progress-bar");
            if (progressBar) {
                progressBar.style.width = "100%";
                progressBar.style.transition = "width 0.3s ease-out";
            }

            setTimeout(() => {
                loader.classList.add("fade-out");

                body.style.overflow = "";

                setTimeout(() => {
                    loader.style.display = "none";
                }, 300); 
            }, 100); 
        }
    }

    if (document.readyState === "complete") {
        setTimeout(hideLoader, 100);
    } else {
        window.addEventListener("load", function() {
            setTimeout(hideLoader, 100);
        });
    }

    setTimeout(hideLoader, 1500);

    const forms = document.querySelectorAll("form");
    forms.forEach((form) => {
        form.addEventListener("submit", function() {

            if (form.checkValidity()) {

                body.style.overflow = "hidden";

                const progressBar = loader.querySelector(".progress-bar");
                if (progressBar) {
                    progressBar.style.transition = "none";
                    progressBar.style.width = "0%";
                    void progressBar.offsetWidth; 
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