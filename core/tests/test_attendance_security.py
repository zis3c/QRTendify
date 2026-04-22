from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import AttendanceRecord, Session, User
from core.services.signing import make_attendance_record_sig


class AttendanceSecurityTests(TestCase):
    def setUp(self):
        self.creator = User.objects.create_user(
            email="creator@example.com",
            password="pass12345",
            first_name="Creator",
            last_name="User",
        )
        self.attendee = User.objects.create_user(
            email="attendee@example.com",
            password="pass12345",
            first_name="Attendee",
            last_name="User",
        )

        self.session = Session.objects.create(
            creator=self.creator,
            organization=None,
            title="Personal Session",
            start_time=timezone.now(),
            end_time=timezone.now() + timezone.timedelta(hours=1),
            status="Open",
        )
        self.record = AttendanceRecord.objects.create(
            session=self.session,
            user=self.attendee,
            check_in_method="Manual",
            is_verified=True,
            device_ip="127.0.0.1",
        )

    def test_success_requires_sig_when_anonymous(self):
        url = reverse("attendance_success", args=[self.record.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 403)

    def test_proof_requires_sig_when_anonymous(self):
        url = reverse("download_proof", kwargs={"record_id": self.record.id})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 403)

    def test_success_allows_sig_when_anonymous(self):
        sig = make_attendance_record_sig(self.record.id)
        url = reverse("attendance_success", args=[self.record.id]) + f"?sig={sig}"
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Attendance Recorded!")

    def test_proof_allows_sig_when_anonymous(self):
        sig = make_attendance_record_sig(self.record.id)
        url = (
            reverse("download_proof", kwargs={"record_id": self.record.id})
            + f"?sig={sig}"
        )
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "application/pdf")
        self.assertTrue(resp.content.startswith(b"%PDF"))
