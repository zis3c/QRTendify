"""
Certificate Management Views

Dedicated views for managing certificate templates separately from session management.
Provides a standalone interface for uploading templates, previewing PDFs, and
positioning attendee names via drag-and-drop.
"""

import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from ..forms import CertificateTemplateForm
from ..models import (
    AttendanceRecord,
    CertificateTemplate,
    GeneratedCertificate,
    Session,
)
from ..services.certificates import generate_and_send_certificate

logger = logging.getLogger(__name__)


@login_required
def certificate_list_view(request):
    """
    Display all sessions with their certificate template status.
    Allows organizers to see which sessions have certificates configured.
    """
    # Get all sessions the user has access to
    user_orgs = request.user.organizations.filter(organizationmember__status="active")

    sessions = (
        Session.objects.filter(
            Q(organization__in=user_orgs) | Q(creator=request.user, organization=None)
        )
        .select_related("organization")
        .prefetch_related(
            "certificatetemplate",
            "attendancerecord_set__user",
            "attendancerecord_set__generatedcertificate",
        )
        .order_by("-created_at")
    )

    # Build session list with certificate status
    sessions_with_status = []
    for session in sessions:
        try:
            cert_template = session.certificatetemplate
            has_template = True
            template_file = (
                cert_template.template_file.name
                if cert_template.template_file
                else None
            )
        except CertificateTemplate.DoesNotExist:
            has_template = False
            template_file = None

        sessions_with_status.append(
            {
                "session": session,
                "has_template": has_template,
                "template_file": template_file,
            }
        )

    context = {
        "sessions_with_status": sessions_with_status,
    }
    return render(request, "certificates/certificate_list.html", context)


@login_required
def certificate_detail_view(request, session_id):
    """
    Manage certificate template for a specific session.
    Handles template upload and configuration with visual preview.
    """
    # Security check: User must have access to this session
    try:
        session = Session.objects.get(
            Q(
                organization__in=request.user.organizations.filter(
                    organizationmember__status="active"
                )
            )
            | Q(creator=request.user, organization=None),
            pk=session_id,
        )
    except Session.DoesNotExist:
        messages.error(
            request, "Session not found or you don't have permission to access it."
        )
        return redirect("certificate_list")

    # Get existing template if it exists
    try:
        certificate_template = CertificateTemplate.objects.get(session=session)
        is_new = False
    except CertificateTemplate.DoesNotExist:
        certificate_template = None
        is_new = True

    if request.method == "POST":
        if certificate_template:
            form = CertificateTemplateForm(
                request.POST, request.FILES, instance=certificate_template
            )
        else:
            form = CertificateTemplateForm(request.POST, request.FILES)

        if form.is_valid():
            cert_template = form.save(commit=False)
            cert_template.session = session
            cert_template.save()

            messages.success(request, "Certificate template saved successfully.")
            return redirect("certificate_detail", session_id=session.pk)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        if certificate_template:
            form = CertificateTemplateForm(instance=certificate_template)
        else:
            form = CertificateTemplateForm()

    # Get certificate generation statistics
    total_attendees = AttendanceRecord.objects.filter(session=session).count()
    generated_certs = GeneratedCertificate.objects.filter(
        attendance_record__session=session
    ).count()

    context = {
        "session": session,
        "certificate_template": certificate_template,
        "form": form,
        "is_new": is_new,
        "total_attendees": total_attendees,
        "generated_certs": generated_certs,
        "attendance_records": AttendanceRecord.objects.filter(
            session=session
        ).select_related("user", "generatedcertificate"),
    }
    return render(request, "certificates/certificate_detail.html", context)


@login_required
def certificate_update_position_api(request, template_id):
    """
    API endpoint to update the name position coordinates via AJAX.
    Called when user drags the name element on the PDF preview.
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    try:
        # Security check
        template = CertificateTemplate.objects.get(pk=template_id)
        session = template.session

        # Verify user has access to this session
        user_orgs = request.user.organizations.filter(
            organizationmember__status="active"
        )
        if not (
            session.organization in user_orgs
            or (session.organization is None and session.creator == request.user)
        ):
            return JsonResponse({"error": "Unauthorized"}, status=403)

        # Update coordinates
        x_position = request.POST.get("x_position")
        y_position = request.POST.get("y_position")

        if x_position is not None and y_position is not None:
            template.name_x_position = int(float(x_position))
            template.name_y_position = int(float(y_position))

            # Also update font size if provided
            font_size = request.POST.get("font_size")
            if font_size:
                template.font_size = int(float(font_size))

            template.save()

            return JsonResponse(
                {
                    "success": True,
                    "x_position": template.name_x_position,
                    "y_position": template.name_y_position,
                    "font_size": template.font_size,
                }
            )
        else:
            return JsonResponse({"error": "Missing coordinates"}, status=400)

    except CertificateTemplate.DoesNotExist:
        return JsonResponse({"error": "Template not found"}, status=404)
    except Exception as e:
        logger.error(f"Error updating certificate position: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_POST
def certificate_send_api(request, session_id):
    """
    API endpoint to manually trigger certificate sending.
    Supports sending to a single attendee or all pending attendees.
    """
    try:
        session = Session.objects.get(pk=session_id)

        # Permission check
        user_orgs = request.user.organizations.filter(
            organizationmember__status="active"
        )
        if not (
            session.organization in user_orgs
            or (session.organization is None and session.creator == request.user)
        ):
            return JsonResponse({"error": "Unauthorized"}, status=403)

        action = request.POST.get("action")

        if action == "single":
            record_id = request.POST.get("record_id")
            try:
                record = AttendanceRecord.objects.get(pk=record_id, session=session)
                success, error = generate_and_send_certificate(record)
                if success:
                    return JsonResponse(
                        {"success": True, "message": f"Sent to {record.user.email}"}
                    )
                else:
                    return JsonResponse({"success": False, "error": error})
            except AttendanceRecord.DoesNotExist:
                return JsonResponse({"success": False, "error": "Record not found"})

        elif action == "all":
            records = AttendanceRecord.objects.filter(session=session)
            sent_count = 0
            errors = []

            for record in records:
                # Check if already sent successfully to avoid spamming
                if (
                    hasattr(record, "generatedcertificate")
                    and record.generatedcertificate.email_sent
                ):
                    continue

                success, error = generate_and_send_certificate(record)
                if success:
                    sent_count += 1
                else:
                    errors.append(f"{record.user.email}: {error}")

            return JsonResponse(
                {
                    "success": True,
                    "sent_count": sent_count,
                    "errors": errors if errors else None,
                }
            )

        else:
            return JsonResponse({"error": "Invalid action"}, status=400)

    except Session.DoesNotExist:
        return JsonResponse({"error": "Session not found"}, status=404)
    except Exception as e:
        logger.error(f"Error in certificate send API: {str(e)}", exc_info=True)
        return JsonResponse({"error": str(e)}, status=500)
