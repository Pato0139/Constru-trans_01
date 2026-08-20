// ---- Control del checkbox y botón ----
const checkTerminos = document.getElementById('aceptarTerminos');
const btnRegistrar  = document.getElementById('btnRegistrar');

checkTerminos.addEventListener('change', function() {
    btnRegistrar.disabled = !this.checked;
});

// ---- Modal Términos ----
function abrirTerminos() {
    document.getElementById('terminosModalRegistro').classList.remove('d-none');
    document.body.style.overflow = 'hidden';
}
function cerrarTerminos() {
    document.getElementById('terminosModalRegistro').classList.add('d-none');
    document.body.style.overflow = '';
}
function aceptarTerminosDesdeModal() {
    checkTerminos.checked = true;
    checkTerminos.dispatchEvent(new Event('change'));
    cerrarTerminos();
}
document.getElementById('terminosBackdropRegistro').addEventListener('click', cerrarTerminos);

// ---- Modal Privacidad (desde registro) ----
function abrirPrivacidadRegistro() {
    document.getElementById('privacidadModalRegistro').classList.remove('d-none');
    document.body.style.overflow = 'hidden';
}
function cerrarPrivacidadRegistro() {
    document.getElementById('privacidadModalRegistro').classList.add('d-none');
    document.body.style.overflow = '';
}
document.getElementById('privacidadBackdropRegistro').addEventListener('click', cerrarPrivacidadRegistro);

// ---- Cerrar con Escape ----
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        cerrarTerminos();
        cerrarPrivacidadRegistro();
    }
});

/**
 * Alterna la visibilidad de un campo de contraseña
 * @param {string} inputId - ID del input de contraseña
 * @param {string} iconId  - ID del ícono toggle
 */
function togglePassword(inputId, iconId) {
    const passwordInput = document.getElementById(inputId);
    const toggleIcon = document.getElementById(iconId);
    if (passwordInput.type === 'password') {
        passwordInput.type = 'text';
        toggleIcon.classList.replace('bi-eye-slash', 'bi-eye');
    } else {
        passwordInput.type = 'password';
        toggleIcon.classList.replace('bi-eye', 'bi-eye-slash');
    }
}

/**
 * Calcula la fortaleza de una contraseña en porcentaje
 * @param {string} password - Contraseña a evaluar
 * @returns {number} Valor entre 0 y 100
 */
function calculatePasswordStrength(password) {
    let strength = 0;
    if (password.length >= 8)  strength += 25;
    if (password.length >= 12) strength += 25;
    if (/[A-Z]/.test(password)) strength += 25;
    if (/[0-9]/.test(password)) strength += 25;
    if (/[^A-Za-z0-9]/.test(password)) strength += 25;
    return Math.min(strength, 100);
}

/**
 * Devuelve texto y clase CSS según el nivel de fortaleza
 * @param {number} strength - Porcentaje de fortaleza
 * @returns {{text: string, color: string}|string}
 */
function getStrengthText(strength) {
    if (strength === 0) return '';
    if (strength < 30) return { text: 'Muy débil', color: 'bg-danger' };
    if (strength < 60) return { text: 'Débil',     color: 'bg-warning' };
    if (strength < 85) return { text: 'Media',      color: 'bg-info' };
    return { text: 'Segura', color: 'bg-success' };
}

const passwordInput = document.getElementById('id_contrasena');
const strengthBar   = document.getElementById('passwordStrengthBar');
const strengthText  = document.getElementById('passwordStrengthText');

if (passwordInput) {
    passwordInput.addEventListener('input', function() {
        const strength     = calculatePasswordStrength(this.value);
        const strengthInfo = getStrengthText(strength);

        strengthBar.style.width = strength + '%';
        strengthBar.setAttribute('aria-valuenow', strength);
        strengthBar.className = 'progress-bar';

        if (strengthInfo.color) {
            strengthBar.classList.add(strengthInfo.color);
        }

        strengthText.textContent = strengthInfo.text || '';
        if (strengthInfo.text) {
            strengthText.className = 'small mt-1';
            if (strengthInfo.color === 'bg-danger')  strengthText.classList.add('text-danger');
            else if (strengthInfo.color === 'bg-warning') strengthText.classList.add('text-warning');
            else if (strengthInfo.color === 'bg-info')    strengthText.classList.add('text-info');
            else if (strengthInfo.color === 'bg-success') strengthText.classList.add('text-success');
        }
    });
}
