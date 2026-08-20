/**
 * Abre el modal de Términos y Condiciones en el login
 */
function abrirTerminosLogin() {
    document.getElementById('terminosModalLogin').classList.remove('d-none');
    document.body.style.overflow = 'hidden';
}

/**
 * Cierra el modal de Términos y Condiciones en el login
 */
function cerrarTerminosLogin() {
    document.getElementById('terminosModalLogin').classList.add('d-none');
    document.body.style.overflow = '';
}

/**
 * Abre el modal de Política de Privacidad en el login
 */
function abrirPrivacidadLogin() {
    document.getElementById('privacidadModalLogin').classList.remove('d-none');
    document.body.style.overflow = 'hidden';
}

/**
 * Cierra el modal de Política de Privacidad en el login
 */
function cerrarPrivacidadLogin() {
    document.getElementById('privacidadModalLogin').classList.add('d-none');
    document.body.style.overflow = '';
}

document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('terminosBackdropLogin').addEventListener('click', cerrarTerminosLogin);
    document.getElementById('privacidadBackdropLogin').addEventListener('click', cerrarPrivacidadLogin);
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            cerrarTerminosLogin();
            cerrarPrivacidadLogin();
        }
    });
});

/**
 * Alterna la visibilidad del campo de contraseña en el login
 */
function togglePassword() {
    const passwordInput = document.getElementById('password');
    const toggleIcon = document.getElementById('toggleIcon');
    if (passwordInput.type === 'password') {
        passwordInput.type = 'text';
        toggleIcon.classList.replace('bi-eye-slash', 'bi-eye');
    } else {
        passwordInput.type = 'password';
        toggleIcon.classList.replace('bi-eye', 'bi-eye-slash');
    }
}

/**
 * Alterna el estado del checkbox mock de reCAPTCHA
 */
function toggleCaptcha() {
    const box   = document.getElementById('captcha-box');
    const input = document.getElementById('id_captcha');
    const icon  = document.getElementById('captcha-icon');
    const widget = box.closest('.recaptcha-mock');
    if (!input.checked) {
        box.classList.add('checked');
        icon.classList.remove('d-none');
        input.checked = true;
        widget.setAttribute('aria-checked', 'true');
    } else {
        box.classList.remove('checked');
        icon.classList.add('d-none');
        input.checked = false;
        widget.setAttribute('aria-checked', 'false');
    }
}

function handleCaptchaKeydown(event) {
    if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        toggleCaptcha();
    }
}
