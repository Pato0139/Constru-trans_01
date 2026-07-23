from django.test import SimpleTestCase

from usuarios.models import Usuario, foto_perfil_upload_path


class FotoPerfilUploadPathTests(SimpleTestCase):
    def test_upload_path_uses_media_folder_for_user_images(self):
        usuario = Usuario(pk=7)

        path = foto_perfil_upload_path(usuario, "avatar.png")

        self.assertTrue(path.startswith("perfiles/usuarios/"))
        self.assertIn("usuario_7", path)
        self.assertTrue(path.endswith(".png"))
