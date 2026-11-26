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
 * Estado y lógica de verificación CAPTCHA visual validada en servidor
 */
let _captchaChallengeId = '';
let _captchaVerified = false;
let _captchaLoading = false;

function _getCsrfToken() {
    const input = document.querySelector('input[name="csrfmiddlewaretoken"]');
    return input ? input.value : '';
}

function _setCaptchaFeedback(message) {
    const el = document.getElementById('captcha-feedback');
    if (!el) return;
    if (message) {
        el.textContent = message;
        el.classList.remove('d-none');
    } else {
        el.textContent = '';
        el.classList.add('d-none');
    }
}

function _resetCaptchaVisual() {
    const box = document.getElementById('captcha-box');
    const icon = document.getElementById('captcha-icon');
    const spinner = document.getElementById('captcha-spinner');
    const input = document.getElementById('id_captcha');
    const tokenInput = document.getElementById('id_captcha_token');
    const widget = document.getElementById('captcha-widget');
    const label = document.getElementById('captcha-label');

    _captchaVerified = false;
    if (input) input.checked = false;
    if (tokenInput) tokenInput.value = '';
    if (box) box.classList.remove('checked');
    if (icon) icon.classList.add('d-none');
    if (spinner) spinner.classList.add('d-none');
    if (widget) {
        widget.classList.remove('is-verified');
        widget.setAttribute('aria-checked', 'false');
    }
    if (label) label.textContent = 'No soy un robot';
}

async function cargarRetoCaptcha(event) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    if (_captchaLoading) return;

    const widget = document.getElementById('captcha-widget');
    const panel = document.getElementById('captcha-challenge-panel');
    const img = document.getElementById('captcha-challenge-img');
    const answerInput = document.getElementById('captcha-answer-input');
    const spinner = document.getElementById('captcha-spinner');
    const retoUrl = widget ? widget.dataset.retoUrl : '/usuarios/captcha/reto/';

    _captchaLoading = true;
    _setCaptchaFeedback('');
    if (spinner) spinner.classList.remove('d-none');

    try {
        const resp = await fetch(retoUrl, {
            method: 'GET',
            credentials: 'same-origin',
            headers: { 'X-Requested-With': 'XMLHttpRequest' },
        });
        const data = await resp.json();
        if (!resp.ok || !data.challenge_id || !data.image) {
            throw new Error('No se pudo cargar el reto.');
        }
        _captchaChallengeId = data.challenge_id;
        if (img) img.src = data.image;
        if (panel) panel.classList.remove('d-none');
        if (answerInput) {
            answerInput.value = '';
            answerInput.focus();
        }
    } catch (_err) {
        _setCaptchaFeedback('No se pudo cargar el código. Intenta nuevamente.');
        if (panel) panel.classList.remove('d-none');
    } finally {
        _captchaLoading = false;
        if (spinner) spinner.classList.add('d-none');
    }
}

async function verificarRetoCaptcha(event) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    if (_captchaLoading) return;

    const widget = document.getElementById('captcha-widget');
    const panel = document.getElementById('captcha-challenge-panel');
    const img = document.getElementById('captcha-challenge-img');
    const answerInput = document.getElementById('captcha-answer-input');
    const verifyBtn = document.getElementById('captcha-verify-btn');
    const box = document.getElementById('captcha-box');
    const icon = document.getElementById('captcha-icon');
    const input = document.getElementById('id_captcha');
    const tokenInput = document.getElementById('id_captcha_token');
    const label = document.getElementById('captcha-label');
    const verificarUrl = widget ? widget.dataset.verificarUrl : '/usuarios/captcha/verificar/';

    const answer = answerInput ? answerInput.value.trim() : '';
    if (!answer) {
        _setCaptchaFeedback('Escribe los caracteres que ves en la imagen.');
        if (answerInput) answerInput.focus();
        return;
    }

    _captchaLoading = true;
    _setCaptchaFeedback('');
    if (verifyBtn) verifyBtn.disabled = true;

    try {
        const resp = await fetch(verificarUrl, {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': _getCsrfToken(),
                'X-Requested-With': 'XMLHttpRequest',
            },
            body: JSON.stringify({
                challenge_id: _captchaChallengeId,
                answer: answer,
            }),
        });
        const data = await resp.json();

        if (resp.ok && data.ok && data.token) {
            _captchaVerified = true;
            if (input) input.checked = true;
            if (tokenInput) tokenInput.value = data.token;
            if (box) box.classList.add('checked');
            if (icon) icon.classList.remove('d-none');
            if (widget) {
                widget.classList.add('is-verified');
                widget.setAttribute('aria-checked', 'true');
            }
            if (label) label.textContent = 'Verificado';
            if (panel) panel.classList.add('d-none');
            _setCaptchaFeedback('');
        } else {
            _resetCaptchaVisual();
            if (data.challenge && data.challenge.challenge_id && data.challenge.image) {
                _captchaChallengeId = data.challenge.challenge_id;
                if (img) img.src = data.challenge.image;
            }
            _setCaptchaFeedback(data.error || 'Código incorrecto. Intenta de nuevo.');
            if (answerInput) {
                answerInput.value = '';
                answerInput.focus();
            }
        }
    } catch (_err) {
        _setCaptchaFeedback('Error de conexión al verificar. Intenta de nuevo.');
    } finally {
        _captchaLoading = false;
        if (verifyBtn) verifyBtn.disabled = false;
    }
}

function toggleCaptcha() {
    if (_captchaVerified) {
        return;
    }
    const panel = document.getElementById('captcha-challenge-panel');
    if (panel && !panel.classList.contains('d-none') && _captchaChallengeId) {
        const answerInput = document.getElementById('captcha-answer-input');
        if (answerInput) answerInput.focus();
        return;
    }
    cargarRetoCaptcha();
}

function handleCaptchaKeydown(event) {
    if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        toggleCaptcha();
    }
}

document.addEventListener('DOMContentLoaded', function() {
    const answerInput = document.getElementById('captcha-answer-input');
    if (answerInput) {
        answerInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                verificarRetoCaptcha(e);
            }
        });
    }

    const loginForm = document.querySelector('form[method="POST"]');
    if (loginForm) {
        loginForm.addEventListener('submit', function(e) {
            const tokenInput = document.getElementById('id_captcha_token');
            if (!_captchaVerified || !tokenInput || !tokenInput.value) {
                e.preventDefault();
                toggleCaptcha();
                _setCaptchaFeedback('Completa este reto antes de iniciar sesión.');
            }
        });
    }
});
