(function () {
    "use strict";

    document.addEventListener("DOMContentLoaded", function () {
        var dropdown = document.querySelector(
            ".inventory-materials-page .dropdown, .inventory-types-page .dropdown"
        );
        if (!dropdown || !window.bootstrap) return;

        var toggle = dropdown.querySelector("[data-bs-toggle='dropdown']");
        if (!toggle) return;

        var instance = bootstrap.Dropdown.getOrCreateInstance(toggle);
        var closeTimer;

        function scheduleClose() {
            window.clearTimeout(closeTimer);
            closeTimer = window.setTimeout(function () {
                if (!dropdown.matches(":hover") && !dropdown.contains(document.activeElement)) {
                    instance.hide();
                }
            }, 120);
        }

        dropdown.addEventListener("mouseleave", scheduleClose);
        dropdown.addEventListener("mouseenter", function () {
            window.clearTimeout(closeTimer);
        });

        dropdown.querySelectorAll(".dropdown-item").forEach(function (item) {
            item.addEventListener("click", function () {
                instance.hide();
            });
        });

        toggle.addEventListener("blur", function () {
            scheduleClose();
        });

        dropdown.addEventListener("focusout", function (event) {
            if (!dropdown.contains(event.relatedTarget)) scheduleClose();
        });
    });
})();
