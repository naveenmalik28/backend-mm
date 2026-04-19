from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from kombu.exceptions import OperationalError as KombuOperationalError


User = get_user_model()


class WelcomeEmailSignalTests(TestCase):
    def test_regular_user_creation_queues_welcome_email_after_commit(self):
        with patch("apps.users.signals.transaction.on_commit", side_effect=lambda callback: callback()) as mocked_on_commit, patch(
            "apps.users.signals.send_welcome_email.delay"
        ) as mocked_delay:
            user = User.objects.create_user(
                email="reader@example.com",
                username="reader",
                password="password123",
            )

        mocked_on_commit.assert_called_once()
        mocked_delay.assert_called_once_with(str(user.pk))

    def test_superuser_creation_does_not_queue_welcome_email(self):
        with patch("apps.users.signals.transaction.on_commit") as mocked_on_commit, patch(
            "apps.users.signals.send_welcome_email.delay"
        ) as mocked_delay:
            User.objects.create_superuser(
                email="admin@example.com",
                username="admin",
                password="password123",
            )

        mocked_on_commit.assert_not_called()
        mocked_delay.assert_not_called()

    def test_user_creation_succeeds_when_broker_is_unavailable(self):
        with patch("apps.users.signals.transaction.on_commit", side_effect=lambda callback: callback()), patch(
            "apps.users.signals.send_welcome_email.delay",
            side_effect=KombuOperationalError("broker unavailable"),
        ):
            user = User.objects.create_user(
                email="offline@example.com",
                username="offline",
                password="password123",
            )

        self.assertEqual(user.email, "offline@example.com")
