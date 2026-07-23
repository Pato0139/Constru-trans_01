/**
 * @file Gestión de carga de imagen de perfil con validación y vista previa
 */

/**
 * Inicializa el evento de cambio de foto de perfil
 * @listens DOMContentLoaded
 */
document.addEventListener('DOMContentLoaded', function() {
    const fotoPerfilInput = document.getElementById('foto_perfil_input');
    if (fotoPerfilInput) {
        /**
         * Valida y muestra vista previa de la imagen seleccionada
         * @listens change
         */
        fotoPerfilInput.addEventListener('change', function(evt) {
            const [file] = this.files;
            if (file) {
                // Validate size (max 50MB)
                if (file.size > 50 * 1024 * 1024) {
                    alert("La archivo es demasiado grande. El tamaño máximo permitido es 50MB.");
                    this.value = '';
                    return;
                }

                // Show preview
                const previewImg = document.getElementById('preview-image');
                const previewInitials = document.getElementById('preview-initials');
                
                if (previewInitials) {
                    previewInitials.style.display = 'none';
                }
                
                previewImg.style.display = 'block';
                previewImg.src = URL.createObjectURL(file);
            }
        });
    }
});
