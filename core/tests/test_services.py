from django.test import TestCase
from django.utils import timezone

from core.models import (
    AttendanceRecord,
    CertificateTemplate,
    Organization,
    OrganizationMember,
    Session,
    User,
)
from core.services.certificates import (
    send_certificate_for_record,
    should_send_certificate_for_record,
)
from core.services.session_access import user_can_access_session


class ServiceTests(TestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(
            email="a@example.com",
            password="pass12345",
            first_name="A",
            last_name="User",
        )
        self.user_b = User.objects.create_user(
            email="b@example.com",
            password="pass12345",
            first_name="B",
            last_name="User",
        )
        self.org = Organization.objects.create(name="Org", domain="example.com")
        OrganizationMember.objects.create(
            organization=self.org, user=self.user_a, role="Member", status="active"
        )

    def test_user_can_access_org_session_via_membership(self):
        session = Session.objects.create(
            organization=self.org,
            creator=self.user_b,
            title="Org Session",
            start_time=timezone.now(),
            end_time=timezone.now() + timezone.timedelta(hours=1),
            status="Open",
        )
        self.assertTrue(user_can_access_session(self.user_a, session))
        self.assertFalse(
            user_can_access_session(
                self.user_b,
                Session.objects.create(
                    organization=None,
                    creator=self.user_a,
                    title="Personal",
                    start_time=timezone.now(),
                    end_time=timezone.now() + timezone.timedelta(hours=1),
                    status="Open",
                ),
            )
        )

    def test_certificate_service_no_template(self):
        session = Session.objects.create(
            organization=None,
            creator=self.user_a,
            title="Personal",
            start_time=timezone.now(),
            end_time=timezone.now() + timezone.timedelta(hours=1),
            status="Open",
        )
        record = AttendanceRecord.objects.create(
            session=session,
            user=self.user_b,
            check_in_method="Manual",
            is_verified=True,
            device_ip="127.0.0.1",
        )
        self.assertFalse(should_send_certificate_for_record(record))
        sent, error = send_certificate_for_record(record)
        self.assertFalse(sent)
        self.assertIsNone(error)

    def test_certificate_service_inactive_template(self):
        session = Session.objects.create(
            organization=None,
            creator=self.user_a,
            title="Personal2",
            start_time=timezone.now(),
            end_time=timezone.now() + timezone.timedelta(hours=1),
            status="Open",
        )
        record = AttendanceRecord.objects.create(
            session=session,
            user=self.user_b,
            check_in_method="Manual",
            is_verified=True,
            device_ip="127.0.0.1",
        )
        CertificateTemplate.objects.create(
            session=session, is_active=False, template_file="dummy.pdf"
        )
        self.assertFalse(should_send_certificate_for_record(record))
        sent, error = send_certificate_for_record(record)
        self.assertFalse(sent)
        self.assertIsNone(error)
