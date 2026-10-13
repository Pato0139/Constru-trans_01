from io import BytesIO
from types import SimpleNamespace
from unittest.mock import Mock

from django.contrib.messages.middleware import MessageMiddleware
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory, SimpleTestCase
from django.urls import reverse
from PIL import Image

from usuarios.forms import FotoPerfilForm
from usuarios.models import Usuario, foto_perfil_upload_path
from usuarios.views import editar_perfil


class FotoPerfilUploadPathTests(SimpleTestCase):
    def test_upload_path_uses_media_folder_for_user_images(self):
        usuario = Usuario(pk=7)

        path = foto_perfil_upload_path(usuario, "avatar.png")

        self.assertTrue(path.startswith("perfiles/usuarios/"))
        self.assertIn("usuario_7", path)
        self.assertTrue(path.endswith(".png"))

    def test_profile_form_accepts_supported_image(self):
        image = Image.new("RGB", (2, 2), color="orange")
        image_file = BytesIO()
        image.save(image_file, format="PNG")

        form = FotoPerfilForm(
            data={},
            files={
                "foto_perfil": SimpleUploadedFile(
                    "avatar.png", image_file.getvalue(), content_type="image/png"
                )
            },
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_profile_form_rejects_non_image_file(self):
        form = FotoPerfilForm(
            data={},
            files={
                "foto_perfil": SimpleUploadedFile(
                    "avatar.jpg", b"not an image", content_type="image/jpeg"
                )
            },
        )

        self.assertFalse(form.is_valid())

    def test_selecting_profile_photo_saves_and_redirects(self):
        image = Image.new("RGB", (2, 2), color="orange")
        image_file = BytesIO()
        image.save(image_file, format="PNG")
        request = RequestFactory().post(
            reverse("usuarios:editar_perfil"),
            {
                "action": "upload_photo",
                "foto_perfil": SimpleUploadedFile(
                    "avatar.png", image_file.getvalue(), content_type="image/png"
                ),
            },
        )
        SessionMiddleware(lambda request: None).process_request(request)
        MessageMiddleware(lambda request: None).process_request(request)
        request.user = SimpleNamespace(
            is_authenticated=True,
            foto_perfil=None,
            save=Mock(),
        )

        response = editar_perfil(request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("usuarios:editar_perfil"))
        request.user.save.assert_called_once_with(update_fields=["foto_perfil"])
