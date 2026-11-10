/**
 * Manejador de eventos del navbar para cambiar temas y filtros de daltonismo
 */
function closeAccessibilityMenus() {
    document.querySelectorAll('.js-accessibility-dropdown').forEach((dropdown) => {
        const toggle = dropdown.querySelector('[data-bs-toggle="dropdown"]');
        if (toggle && window.bootstrap?.Dropdown) {
            window.bootstrap.Dropdown.getOrCreateInstance(toggle).hide();
        }
    });
}

document.addEventListener('click', (event) => {
    // Manejar cambio de tema
    const themeLink = event.target.closest('.theme-option');
    if (themeLink) {
        event.preventDefault();
        const theme = themeLink.dataset.themeValue;
        if (typeof window.setTheme !== 'function') {
            console.error('No se pudo cambiar el tema: el módulo de preferencias no está disponible.');
            return;
        }
        window.setTheme(theme);
        closeAccessibilityMenus();
        return;
    }

    // Manejar cambio de filtro de daltonismo
    const daltonismLink = event.target.closest('.daltonism-option');
    if (daltonismLink) {
        event.preventDefault();
        const mode = daltonismLink.dataset.daltonismValue;
        if (typeof setDaltonism === 'function') setDaltonism(mode);
        closeAccessibilityMenus();
        return;
    }

    // Cierra el menú al pulsar fuera del bloque de accesibilidad.
    if (!event.target.closest('.js-accessibility-dropdown')) {
        closeAccessibilityMenus();
    }
});

/**
 * Sincronización en tiempo real de notificaciones (ej. cuando el cliente corrige un pago)
 */
(function initLiveNotifications() {
    const seenNotificationKeys = new Set();
    let initialized = false;

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text || '';
        return div.innerHTML;
    }

    function iconClassesForType(tipo) {
        if (tipo === 'info') return { box: 'bg-info-subtle text-info', icon: 'bi-info-circle' };
        if (tipo === 'success') return { box: 'bg-success-subtle text-success', icon: 'bi-check-circle' };
        if (tipo === 'warning') return { box: 'bg-warning-subtle text-warning', icon: 'bi-exclamation-triangle' };
        return { box: 'bg-primary-subtle text-primary', icon: 'bi-bell' };
    }

    function renderNotifItems(items) {
        const listEl = document.getElementById('navbarNotifList');
        if (!listEl) return;
        if (!items || items.length === 0) {
            listEl.innerHTML = `
                <li class="px-3 py-5 text-center text-muted">
                    <i class="bi bi-bell-slash fs-1 d-block mb-3 opacity-25"></i>
                    <p class="mb-0">No tienes notificaciones</p>
                    <small class="text-muted">Las nuevas notificaciones aparecerán aquí</small>
                </li>`;
            return;
        }
        listEl.innerHTML = items.map((notif) => {
            const cls = iconClassesForType(notif.tipo);
            const unreadClass = !notif.leida ? 'notif-unread-highlight' : '';
            return `
                <li data-notif-id="${notif.id}" data-notif-unread="${!notif.leida ? '1' : '0'}">
                    <a class="dropdown-item rounded-2 p-3 ${unreadClass}" href="${escapeHtml(notif.url)}">
                        <div class="d-flex gap-3">
                            <div class="flex-shrink-0 notif-icon-container">
                                <div class="rounded-circle d-flex align-items-center justify-content-center ${cls.box} navbar-icon-btn">
                                    <i class="bi ${cls.icon} fs-5"></i>
                                </div>
                            </div>
                            <div class="flex-grow-1 min-w-0">
                                <p class="small mb-1 fw-bold text-white text-truncate">${escapeHtml(notif.titulo)}</p>
                                <p class="small mb-1 text-muted text-truncate">${escapeHtml(notif.mensaje)}</p>
                                <span class="small text-muted navbar-notif-date">${escapeHtml(notif.fecha)}</span>
                            </div>
                        </div>
                    </a>
                </li>`;
        }).join('');
    }

    async function pollNotifications() {
        if (document.hidden) return;
        const container = document.getElementById('navbarNotifDropdown');
        const endpoint = container?.dataset?.notifEndpoint;
        if (!endpoint) return;

        try {
            const response = await fetch(endpoint, {
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
                credentials: 'same-origin'
            });
            if (!response.ok) return;
            const data = await response.json();
            const count = Number(data.unread_count || 0);

            const badge = document.getElementById('navbarNotifBadge');
            if (badge) {
                badge.textContent = String(count);
                badge.classList.toggle('d-none', count <= 0);
            }
            const headerBadge = document.getElementById('navbarNotifHeaderBadge');
            if (headerBadge) {
                headerBadge.textContent = `${count} nuevas`;
                headerBadge.classList.toggle('d-none', count <= 0);
            }

            if (Array.isArray(data.items)) {
                renderNotifItems(data.items);
                data.items.forEach((item) => {
                    const key = `${item.id}:${item.fecha_ts || item.fecha}`;
                    if (!initialized) {
                        seenNotificationKeys.add(key);
                    } else if (!item.leida && !seenNotificationKeys.has(key)) {
                        seenNotificationKeys.add(key);
                        if (window.Swal) {
                            window.Swal.fire({
                                toast: true,
                                position: 'top-end',
                                icon: item.tipo === 'warning' ? 'warning' : 'info',
                                title: item.titulo,
                                text: item.mensaje,
                                showConfirmButton: true,
                                confirmButtonText: 'Ver ahora',
                                timer: 9000,
                                timerProgressBar: true
                            }).then((result) => {
                                if (result.isConfirmed && item.url) {
                                    window.location.href = item.url;
                                }
                            });
                        }
                    }
                });
                initialized = true;
            }
        } catch (err) {
            // Silencioso en caso de desconexión temporal
        }
    }

    document.addEventListener('DOMContentLoaded', () => {
        pollNotifications();
        setInterval(pollNotifications, 12000);
    });
})();
