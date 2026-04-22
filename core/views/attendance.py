import logging
from urllib.parse import urlencode
from datetime import timedelta

from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone

from ..forms import AttendanceForm, CodeRedirectForm
from ..models import (
    AttendanceCode,
    AttendanceRecord,
    DeviceLog,
    DynamicQrToken,
    SessionSetting,
    User,
)
from ..services.certificates import send_certificate_for_record
from ..services.ip_reputation import check_ip_reputation
from ..services.pdf import build_attendance_proof_pdf
from ..services.session_access import user_can_access_session
from ..services.signing import make_attendance_record_sig, verify_attendance_record_sig

logger = logging.getLogger(__name__)

_ATTENDANCE_SIG_MAX_AGE_SECONDS = 60 * 60 * 24 * 7  # 7 days


def attendance_form_view(request):
    """
    Attendance check-in form (static code or dynamic token).
    """
    qr_code = request.GET.get("code")
    token = request.GET.get("token")
    error_message = None
    success_message = None
    session = None
    session_setting = None

    try:
        if token:
            dynamic_token = DynamicQrToken.objects.get(token=token)
            if dynamic_token.expires_at < timezone.now():
                error_message = "This QR code has expired."
            else:
                session = dynamic_token.session
                dynamic_token.delete()
        elif qr_code:
            attendance_code = AttendanceCode.objects.get(static_qr_string=qr_code)
            session = attendance_code.session
        else:
            error_message = "Invalid attendance link."

        if session:
            session_setting = SessionSetting.objects.get(session=session)

            if session.status != "Open":
                error_message = f"This session is currently {session.status.lower()} and not accepting attendance."

            if session_setting.check_in_window_minutes > 0 and session.status == "Open":
                close_time = session.start_time + timedelta(
                    minutes=session_setting.check_in_window_minutes
                )
                if timezone.now() > close_time:
                    error_message = f"Check-in window closed at {close_time.strftime('%I:%M %p')}. You are too late."

    except (
        DynamicQrToken.DoesNotExist,
        AttendanceCode.DoesNotExist,
        SessionSetting.DoesNotExist,
    ):
        error_message = "Invalid or expired QR code."

    form = AttendanceForm(request.POST or None)

    if request.method == "POST" and session and not error_message and form.is_valid():
        name = form.cleaned_data["name"]
        email = form.cleaned_data["email"]

        ip_address = request.META.get("REMOTE_ADDR", "")
        rep = check_ip_reputation(ip_address)
        if rep and rep.is_blocked:
            error_message = (
                "Attendance from a VPN, Proxy, or Data Center is not allowed."
            )
            return render(
                request,
                "form_attendance.html",
                {
                    "form": form,
                    "error_message": error_message,
                    "session": session,
                    "session_setting": session_setting,
                },
            )

        if session_setting and session_setting.is_location_required:
            attendee_lat = form.cleaned_data.get("latitude")
            attendee_lon = form.cleaned_data.get("longitude")
            if not attendee_lat or not attendee_lon:
                error_message = "Location is required for this session. Please enable location services in your browser and try again."
                return render(
                    request,
                    "form_attendance.html",
                    {
                        "form": form,
                        "error_message": error_message,
                        "session": session,
                        "session_setting": session_setting,
                    },
                )

        user, _created = User.objects.get_or_create(
            email=email,
            defaults={"first_name": name, "last_name": "", "sso_provider": "Attendee"},
        )

        record, created = AttendanceRecord.objects.get_or_create(
            session=session,
            user=user,
            defaults={
                "check_in_method": "DynamicQR" if token else "StaticQR",
                "is_verified": True,
                "device_ip": ip_address,
            },
        )

        if not created:
            error_message = (
                "Your attendance has already been recorded for this session."
            )
        else:
            if session_setting and session_setting.is_location_required:
                DeviceLog.objects.create(
                    attendance_record=record,
                    latitude=form.cleaned_data.get("latitude"),
                    longitude=form.cleaned_data.get("longitude"),
                )

            sent, _error = send_certificate_for_record(record)
            if sent:
                success_message = "Certificate sent successfully."

            sig = make_attendance_record_sig(record.id)
            query = urlencode(
                {"sent": "true" if success_message else "false", "sig": sig}
            )
            return redirect(
                f"{reverse('attendance_success', args=[record.id])}?{query}"
            )

        form = AttendanceForm()

    return render(
        request,
        "form_attendance.html",
        {
            "form": form,
            "error_message": error_message,
            "success_message": success_message,
            "session": session,
            "session_setting": session_setting,
        },
    )


def attendance_success_view(request, record_id):
    """Success page after check-in."""
    try:
        record = AttendanceRecord.objects.get(pk=record_id)
    except AttendanceRecord.DoesNotExist:
        return redirect("landing_page")

    sig = request.GET.get("sig")
    is_authorized = False

    if request.user.is_authenticated and user_can_access_session(
        request.user, record.session
    ):
        is_authorized = True
    elif sig and verify_attendance_record_sig(
        record.id, sig, max_age_seconds=_ATTENDANCE_SIG_MAX_AGE_SECONDS
    ):
        is_authorized = True

    if not is_authorized:
        return HttpResponse("Forbidden", status=403)

    return render(
        request,
        "attendance_success.html",
        {"record": record, "sig": sig or make_attendance_record_sig(record.id)},
    )


def download_attendance_proof_view(request, record_id):
    """Generate a PDF proof for a single attendance record."""
    try:
        record = AttendanceRecord.objects.select_related(
            "session", "user", "devicelog"
        ).get(pk=record_id)
        session_setting = record.session.sessionsetting
    except AttendanceRecord.DoesNotExist:
        return redirect("landing_page")
    except SessionSetting.DoesNotExist:
        session_setting = None

    sig = request.GET.get("sig")
    is_authorized = False

    if request.user.is_authenticated and user_can_access_session(
        request.user, record.session
    ):
        is_authorized = True
    elif sig and verify_attendance_record_sig(
        record.id, sig, max_age_seconds=_ATTENDANCE_SIG_MAX_AGE_SECONDS
    ):
        is_authorized = True

    if not is_authorized:
        return HttpResponse("Forbidden", status=403)

    pdf_bytes = build_attendance_proof_pdf(record, session_setting)
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="attendance_proof_{record.session.title}.pdf"'
    )
    return response


def code_redirect_view(request):
    """Redirection based on a 4-digit code (static or dynamic)."""
    error_message = None
    if request.method == "POST":
        form = CodeRedirectForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data["code"]
            try:
                dynamic_token = DynamicQrToken.objects.get(
                    verification_code=code, expires_at__gt=timezone.now()
                )
                return redirect(
                    f"{reverse('attendance_form')}?token={dynamic_token.token}"
                )

            except DynamicQrToken.DoesNotExist:
                try:
                    attendance_code = AttendanceCode.objects.get(
                        verification_number=code
                    )
                    session_setting = SessionSetting.objects.get(
                        session=attendance_code.session
                    )

                    if session_setting.is_dynamic_qr:
                        error_message = "That code is invalid. This session uses a dynamic code that changes every 2 minutes."
                    else:
                        return redirect(
                            f"{reverse('attendance_form')}?code={attendance_code.static_qr_string}"
                        )

                except (AttendanceCode.DoesNotExist, SessionSetting.DoesNotExist):
                    error_message = "Invalid 4-digit code. Please try again."
    else:
        form = CodeRedirectForm()

    return render(
        request,
        "form_code_redirect.html",
        {"form": form, "error_message": error_message},
    )
