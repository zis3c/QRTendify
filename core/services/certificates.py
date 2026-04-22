"""
Certificate generation, email delivery, and orchestration services.

This module handles PDF certificate generation by overlaying attendee names
on template PDFs, sending them via email, and providing the public API
used by views and attendance check-in logic.
"""

from __future__ import annotations

import logging
import os
from io import BytesIO

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.mail import EmailMessage
from django.utils import timezone
from PyPDF2 import PdfReader, PdfWriter
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas

from ..models import (
    AttendanceRecord,
    CertificateTemplate,
    GeneratedCertificate,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------


def hex_to_rgb(hex_color: str) -> tuple[float, float, float]:
    """Convert hex color (e.g., '#FF0000') to RGB tuple (0-1 scale)."""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) / 255.0 for i in (0, 2, 4))


# ---------------------------------------------------------------------------
# Certificate generation
# ---------------------------------------------------------------------------


def generate_certificate(
    attendance_record: AttendanceRecord,
) -> tuple[bool, str | None, str | None]:
    """
    Generate a personalized certificate for an attendee.

    Returns:
        tuple: (success, file_path, error_message)
    """
    try:
        try:
            template = CertificateTemplate.objects.get(
                session=attendance_record.session
            )
        except CertificateTemplate.DoesNotExist:
            logger.info(
                "No certificate template found for session: %s",
                attendance_record.session.title,
            )
            return False, None, "No certificate template configured for this session"

        # Get attendee information
        attendee_name = (
            f"{attendance_record.user.first_name} {attendance_record.user.last_name}"
        ).strip()
        if not attendee_name:
            attendee_name = attendance_record.user.email.split("@")[0]

        # Load the PDF template
        template_path = template.template_file.path
        if not os.path.exists(template_path):
            return False, None, f"Template file not found: {template_path}"

        template_pdf = PdfReader(template_path)
        if len(template_pdf.pages) == 0:
            return False, None, "Template PDF has no pages"

        # Get the first page and its dimensions
        template_page = template_pdf.pages[0]
        page_width = float(template_page.mediabox.width)
        page_height = float(template_page.mediabox.height)

        # Create overlay with attendee name
        packet = BytesIO()
        c = canvas.Canvas(packet, pagesize=(page_width, page_height))

        c.setFont(template.font_name, template.font_size)
        try:
            c.setFillColor(HexColor(template.font_color))
        except Exception:
            c.setFillColorRGB(0, 0, 0)

        c.drawString(template.name_x_position, template.name_y_position, attendee_name)
        c.save()

        # Merge overlay with template
        packet.seek(0)
        overlay_pdf = PdfReader(packet)
        output_pdf = PdfWriter()

        for i, page in enumerate(template_pdf.pages):
            if i == 0:
                page.merge_page(overlay_pdf.pages[0])
            output_pdf.add_page(page)

        output_buffer = BytesIO()
        output_pdf.write(output_buffer)
        output_buffer.seek(0)

        # Generate safe filename
        safe_session_name = "".join(
            ch
            for ch in attendance_record.session.title
            if ch.isalnum() or ch in (" ", "-", "_")
        ).strip()
        safe_attendee_name = "".join(
            ch for ch in attendee_name if ch.isalnum() or ch in (" ", "-", "_")
        ).strip()
        filename = f"certificate_{safe_session_name}_{safe_attendee_name}.pdf"

        # Save to GeneratedCertificate model
        generated_cert, _created = GeneratedCertificate.objects.get_or_create(
            attendance_record=attendance_record
        )
        generated_cert.certificate_file.save(
            filename, ContentFile(output_buffer.getvalue()), save=True
        )

        logger.info(
            "Certificate generated successfully for %s - %s",
            attendee_name,
            attendance_record.session.title,
        )
        return True, generated_cert.certificate_file.path, None

    except Exception as e:
        error_msg = f"Error generating certificate: {e}"
        logger.error(error_msg, exc_info=True)
        return False, None, error_msg


# ---------------------------------------------------------------------------
# Email delivery
# ---------------------------------------------------------------------------


def send_certificate_email(
    attendance_record: AttendanceRecord,
) -> tuple[bool, str | None]:
    """
    Send certificate email to attendee.

    Returns:
        tuple: (success, error_message)
    """
    try:
        try:
            generated_cert = GeneratedCertificate.objects.get(
                attendance_record=attendance_record
            )
        except GeneratedCertificate.DoesNotExist:
            return False, "No certificate found for this attendance record"

        if not generated_cert.certificate_file:
            return False, "Certificate file not found"

        subject = f"Certificate for {attendance_record.session.title}"

        attendee_name = (
            f"{attendance_record.user.first_name} {attendance_record.user.last_name}"
        ).strip()
        if not attendee_name:
            attendee_name = "Attendee"

        org_name = (
            attendance_record.session.organization.name
            if attendance_record.session.organization
            else "QRTendify Team"
        )
        message = (
            f"Dear {attendee_name},\n\n"
            f"Thank you for attending {attendance_record.session.title}!\n\n"
            "Please find attached your personalized certificate of attendance.\n\n"
            "Session Details:\n"
            f"- Title: {attendance_record.session.title}\n"
            f"- Check-in Time: {attendance_record.check_in_time.strftime('%B %d, %Y at %I:%M %p')}\n\n"
            f"Best regards,\n{org_name}\n"
        )

        email = EmailMessage(
            subject=subject,
            body=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[attendance_record.user.email],
        )

        try:
            with open(generated_cert.certificate_file.path, "rb") as cert_file:
                email.attach(
                    os.path.basename(generated_cert.certificate_file.name),
                    cert_file.read(),
                    "application/pdf",
                )
        except Exception as e:
            return False, f"Error attaching certificate: {e}"

        email.send(fail_silently=False)

        generated_cert.email_sent = True
        generated_cert.email_sent_at = timezone.now()
        generated_cert.email_error = None
        generated_cert.save()

        logger.info(
            "Certificate email sent successfully to %s",
            attendance_record.user.email,
        )
        return True, None

    except Exception as e:
        error_msg = f"Error sending certificate email: {e}"
        logger.error(error_msg, exc_info=True)

        try:
            generated_cert = GeneratedCertificate.objects.get(
                attendance_record=attendance_record
            )
            generated_cert.email_error = error_msg
            generated_cert.save()
        except Exception:
            pass

        return False, error_msg


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def should_send_certificate_for_record(record: AttendanceRecord) -> bool:
    """Check whether a certificate should be sent for a given attendance record."""
    template = CertificateTemplate.objects.filter(session=record.session).first()
    return bool(template and template.is_active)


def send_certificate_for_record(record: AttendanceRecord) -> tuple[bool, str | None]:
    """
    Send a certificate if a template exists and is active.

    Returns (sent, error_message). If no template (or inactive), sent=False.
    """
    template = CertificateTemplate.objects.filter(session=record.session).first()
    if not template or not template.is_active:
        return False, None

    success, error = generate_and_send_certificate(record)
    if success:
        return True, None

    if error:
        logger.error("Certificate send failed for %s: %s", record.user.email, error)
    return False, error


def generate_and_send_certificate(
    attendance_record: AttendanceRecord,
) -> tuple[bool, str | None]:
    """
    Complete workflow: generate certificate and send email.

    Returns:
        tuple: (success, error_message)
    """
    success, _file_path, error_msg = generate_certificate(attendance_record)
    if not success:
        if "No certificate template" in str(error_msg):
            logger.info(
                "Skipping certificate for %s - no template configured",
                attendance_record.user.email,
            )
            return True, None
        return False, error_msg

    success, error_msg = send_certificate_email(attendance_record)
    return success, error_msg
