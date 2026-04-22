"""Dashboard, reports, and plan selection views."""

import logging

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render

from ..models import AttendanceRecord, Session, SessionSetting
from ..services.pdf import build_attendance_report_pdf
from ..services.session_access import sessions_user_can_access, user_can_access_session

logger = logging.getLogger(__name__)


@login_required
def dashboard_view(request):
    sessions = sessions_user_can_access(request.user).order_by("-created_at")

    total_sessions = sessions.count()
    open_sessions = sessions.filter(status="Open").count()
    closed_sessions = sessions.filter(status="Closed").count()

    user_job_title = request.user.job_title if request.user.job_title else "Organizer"

    return render(
        request,
        "dashboard.html",
        {
            "sessions": sessions,
            "total_sessions": total_sessions,
            "open_sessions": open_sessions,
            "closed_sessions": closed_sessions,
            "user_job_title": user_job_title,
        },
    )


@login_required
def reports_view(request):
    """List sessions for which the user can download a report."""
    sessions = (
        sessions_user_can_access(request.user)
        .prefetch_related(
            "attendancerecord_set__user",
            "attendancerecord_set__devicelog",
            "sessionsetting",
        )
        .order_by("-created_at")
    )

    return render(request, "reports.html", {"sessions": sessions})


@login_required
def download_report_view(request, pk):
    """Generate a PDF attendance report for a session."""
    try:
        session = Session.objects.get(pk=pk)
        if not user_can_access_session(request.user, session):
            return redirect("dashboard")
        session_setting = SessionSetting.objects.get(session=session)
        attendees = (
            AttendanceRecord.objects.filter(session=session)
            .select_related("user", "devicelog")
            .order_by("-check_in_time")
        )
    except (Session.DoesNotExist, SessionSetting.DoesNotExist):
        return redirect("dashboard")

    pdf_bytes = build_attendance_report_pdf(session, session_setting, attendees)
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="report_{session.title}.pdf"'
    )
    return response


@login_required
def choose_plan_view(request):
    return render(request, "choose_plan.html")
