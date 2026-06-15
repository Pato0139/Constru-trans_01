
document.addEventListener('click', (event) => {
    const trigger = event.target.closest('.js-confirm-db-switch');
    if (!trigger) return;

    event.preventDefault();

    Swal.fire({
        title: '¿Cambiar de Base de Datos?',
        text: 'Al hacer esto cerrarás sesión y deberás volver a iniciar sesión. ¿Deseas continuar?',
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#3085d6',
        cancelButtonColor: '#d33',
        confirmButtonText: 'Sí, continuar',
        cancelButtonText: 'Cancelar'
    }).then((result) => {
        if (result.isConfirmed) {
            trigger.closest('form').submit();
        }
    });
});
