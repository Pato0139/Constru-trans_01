import smtplib
from unittest.mock import Mock, patch

import requests
from django.contrib.auth.views import PasswordResetView
from django.core.mail import EmailMultiAlternatives
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, override_settings

from apps.usuarios.forms import CustomPasswordResetForm
from apps.usuarios.views import CustomPasswordResetView


class PasswordResetViewTests(SimpleTestCase):
    def test_opening_reset_page_does_not_sync_or_check_remote_database(self):
        request = RequestFactory().get("/usuarios/recuperar/")

        with (
            patch.object(CustomPasswordResetView, "get", return_value=HttpResponse("ok")),
            patch("usuarios.views.sync_all_usuarios") as sync_users,
            patch("usuarios.views.conexion_remota_disponible") as remote_available,
        ):
            response = CustomPasswordResetView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        sync_users.assert_not_called()
        remote_available.assert_not_called()

    def test_reset_only_targets_active_users_with_email_and_usable_password(self):
        user_with_email = Mock(email="registered@example.com")
        user_with_email.has_usable_password.return_value = True
        user_without_email = Mock(email="")
        user_without_email.has_usable_password.return_value = True
        query = Mock()
        query.using.return_value = iter([user_with_email, user_without_email])

        with (
            patch("usuarios.forms.User.objects.filter", return_value=query),
            patch("core.utils.conexion_remota_disponible", return_value=False),
        ):
            users = list(CustomPasswordResetForm().get_users("registered"))

        self.assertEqual(users, [user_with_email])

    @override_settings(
        RESEND_API_KEY="test-resend-key",
        RESEND_FROM_EMAIL="Constru-Trans <no-reply@example.com>",
    )
    def test_reset_email_is_sent_through_resend_api(self):
        response = Mock()
        response.json.return_value = {"id": "email_test_123"}

        with (
            patch(
                "usuarios.forms.loader.render_to_string",
                side_effect=["Reset password", "Plain body", "<p>HTML body</p>"],
            ),
            patch("usuarios.forms.requests.post", return_value=response) as post,
        ):
            sent = CustomPasswordResetForm().send_mail(
                "subject.txt",
                "body.txt",
                {},
                None,
                "user@example.com",
                html_email_template_name="body.html",
            )

        self.assertEqual(sent, 1)
        post.assert_called_once_with(
            "https://api.resend.com/emails",
            json={
                "from": "Constru-Trans <no-reply@example.com>",
                "to": ["user@example.com"],
                "subject": "Reset password",
                "text": "Plain body",
                "html": "<p>HTML body</p>",
            },
            headers={"Authorization": "Bearer test-resend-key"},
            timeout=(5, 15),
        )

    @override_settings(RESEND_API_KEY="", RESEND_FROM_EMAIL="")
    def test_uses_configured_django_mail_backend_when_resend_is_not_configured(self):
        email_message = Mock()
        with (
            patch(
                "usuarios.forms.loader.render_to_string",
                side_effect=["Reset password", "Plain body", "<p>HTML body</p>"],
            ),
            patch(
                "usuarios.forms.EmailMultiAlternatives",
                return_value=email_message,
            ) as email_factory,
            patch("usuarios.forms.requests.post") as resend_post,
        ):
            sent = CustomPasswordResetForm().send_mail(
                "subject.txt",
                "body.txt",
                {},
                "Constru-Trans <support@example.com>",
                "user@example.com",
                html_email_template_name="body.html",
            )

        self.assertEqual(sent, email_message.send.return_value)
        email_factory.assert_called_once_with(
            "Reset password",
            "Plain body",
            "Constru-Trans <support@example.com>",
            ["user@example.com"],
        )
        email_message.attach_alternative.assert_called_once_with(
            "<p>HTML body</p>",
            "text/html",
        )
        email_message.send.assert_called_once_with(fail_silently=False)
        resend_post.assert_not_called()

    @override_settings(
        RESEND_API_KEY="test-resend-key",
        RESEND_FROM_EMAIL="Constru-Trans <no-reply@example.com>",
    )
    def test_resend_api_error_is_not_silently_swallowed(self):
        response_error = requests.ConnectionError("connection refused")

        with (
            patch(
                "usuarios.forms.loader.render_to_string",
                side_effect=["Reset password", "Plain body"],
            ),
            patch(
                "usuarios.forms.requests.post",
                side_effect=response_error,
            ),
        ):
            with self.assertRaises(smtplib.SMTPException):
                CustomPasswordResetForm().send_mail(
                    "subject.txt",
                    "body.txt",
                    {},
                    None,
                    "user@example.com",
                )

    @override_settings(
        RESEND_API_KEY="test-resend-key",
        RESEND_FROM_EMAIL="Constru-Trans <no-reply@example.com>",
    )
    def test_delivery_error_is_shown_to_the_user(self):
        request = RequestFactory().post(
            "/usuarios/recuperar/",
            {"email": "user@example.com"},
        )
        view = CustomPasswordResetView()
        view.setup(request)
        form = CustomPasswordResetForm(data={"email": "user@example.com"})

        with patch.object(
            PasswordResetView,
            "form_valid",
            side_effect=smtplib.SMTPException("email delivery failed"),
        ):
            response = view.form_valid(form)

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "No pudimos enviar el correo de recuperación.",
            form.non_field_errors()[0],
        )

    @override_settings(RESEND_API_KEY="", RESEND_FROM_EMAIL="")
    def test_unconfigured_resend_does_not_block_django_mail_backend(self):
        request = RequestFactory().post(
            "/usuarios/recuperar/",
            {"email": "user@example.com"},
        )
        view = CustomPasswordResetView()
        view.setup(request)
        form = CustomPasswordResetForm(data={"email": "user@example.com"})

        with patch.object(
            PasswordResetView,
            "form_valid",
            return_value=HttpResponse("sent"),
        ) as send_reset_email:
            response = view.form_valid(form)

        self.assertEqual(response.status_code, 200)
        send_reset_email.assert_called_once_with(form)

    @override_settings(
        RESEND_API_KEY="test-resend-key",
        RESEND_FROM_EMAIL="Constru-Trans <no-reply@example.com>",
    )
    def test_smtp_failure_is_shown_on_the_reset_form(self):
        request = RequestFactory().post(
            "/usuarios/recuperar/",
            {"email": "user@example.com"},
        )
        view = CustomPasswordResetView()
        view.setup(request)
        form = CustomPasswordResetForm(data={"email": "user@example.com"})

        with patch.object(
            PasswordResetView,
            "form_valid",
            side_effect=smtplib.SMTPAuthenticationError(
                535, b"authentication failed"
            ),
        ):
            response = view.form_valid(form)

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "No pudimos enviar el correo de recuperación.",
            form.non_field_errors()[0],
        )
