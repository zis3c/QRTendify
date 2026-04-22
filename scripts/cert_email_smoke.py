import os
from io import BytesIO, StringIO

import django
from dotenv import load_dotenv
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

load_dotenv()

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "QRTendify_project.settings")
django.setup()

from django.core.files.base import ContentFile  # noqa: E402
from django.test.utils import override_settings  # noqa: E402
from django.utils import timezone  # noqa: E402

from core.services.certificates import generate_and_send_certificate  # noqa: E402
from core.models import (  # noqa: E402
    AttendanceRecord,
    CertificateTemplate,
    GeneratedCertificate,
    Session,
    User,
)


def create_dummy_pdf() -> bytes:
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    c.drawString(100, 750, "CERTIFICATE OF ATTENDANCE")
    c.drawString(100, 700, "This certifies that")
    c.save()
    buffer.seek(0)
    return buffer.getvalue()


@override_settings(EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend")
def main() -> None:
    print("--- Starting Certificate Email Smoke Test ---")

    user, created = User.objects.get_or_create(
        email="test_attendee@example.com",
        defaults={"first_name": "Test", "last_name": "Attendee"},
    )
    if created:
        user.set_password("testpass123")
        user.save()

    session, _ = Session.objects.get_or_create(
        title="Test Workshop 101",
        defaults={
            "description": "A test session for email verification",
            "creator": user,
            "start_time": timezone.now(),
            "end_time": timezone.now() + timezone.timedelta(hours=1),
            "status": "Open",
        },
    )

    record, _ = AttendanceRecord.objects.get_or_create(
        user=user,
        session=session,
        defaults={"check_in_method": "Manual", "is_verified": True, "device_ip": "N/A"},
    )

    template, _ = CertificateTemplate.objects.get_or_create(
        session=session,
        defaults={
            "name_x_position": 100,
            "name_y_position": 600,
            "font_size": 24,
            "font_color": "#000000",
            "is_active": True,
        },
    )
    template.template_file.save(
        "test_template.pdf", ContentFile(create_dummy_pdf()), save=True
    )

    old_stdout = os.sys.stdout
    os.sys.stdout = StringIO()
    try:
        success, error = generate_and_send_certificate(record)
    finally:
        os.sys.stdout = old_stdout

    if not success:
        print(f"FAILED: {error}")
        return

    cert = GeneratedCertificate.objects.get(attendance_record=record)
    print("SUCCESS")
    print(f"Certificate file: {cert.certificate_file.name}")
    print(f"Email sent: {cert.email_sent}")


if __name__ == "__main__":
    main()
