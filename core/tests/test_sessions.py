from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import Session, User


class PersonalSessionTests(TestCase):
    def test_can_create_personal_session(self):
        user = User.objects.create_user(
            email="user@example.com",
            password="pass12345",
            first_name="User",
            last_name="Example",
        )
        self.client.force_login(user)

        start = timezone.localtime(timezone.now())
        end = start + timezone.timedelta(hours=1)

        resp = self.client.post(
            reverse("create_session"),
            data={
                "organization": "",
                "title": "My Personal Session",
                "description": "desc",
                "start_time": start.strftime("%Y-%m-%dT%H:%M"),
                "end_time": end.strftime("%Y-%m-%dT%H:%M"),
                "qr_type": "static",
                "is_location_required": "",
                "check_in_window_minutes": "0",
                "schedule_opening": "now",
                "access_type": "public",
                "email_domain": "",
            },
        )
        self.assertEqual(resp.status_code, 302)

        session = Session.objects.get(title="My Personal Session")
        self.assertIsNone(session.organization_id)
        self.assertEqual(session.creator_id, user.id)

        dashboard = self.client.get(reverse("dashboard"))
        self.assertEqual(dashboard.status_code, 200)
        self.assertContains(dashboard, "My Personal Session")
