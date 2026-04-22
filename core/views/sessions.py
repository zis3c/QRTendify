"""Session CRUD views: list, create, detail, edit, delete."""

import base64
import io
import random
import uuid
from datetime import timedelta

import qrcode
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.generic.edit import UpdateView

from ..forms import SessionEditForm, SessionForm
from ..models import (
    AccessRule,
    AttendanceCode,
    AttendanceRecord,
    OrganizationMember,
    Session,
    SessionSetting,
    User,
)
from ..services.session_access import sessions_user_can_access, user_can_access_session
from ..tasks import open_session_task


@login_required
def session_list_view(request):
    """Session listing with search and filtering."""
    user_job_title = request.user.job_title if request.user.job_title else "Organizer"

    all_user_memberships = (
        OrganizationMember.objects.filter(user=request.user, status="active")
        .select_related("organization")
        .order_by("organization__name")
    )

    org_filter_choices = []
    for membership in all_user_memberships:
        org = membership.organization
        role = membership.role
        display_name = f"{org.name} (Personal Session)" if role == "Owner" else org.name
        org_filter_choices.append(
            {
                "pk": str(org.pk),
                "name": org.name,
                "is_owner": role == "Owner",
                "display": display_name,
            }
        )

    sessions_queryset = sessions_user_can_access(request.user).order_by("-created_at")

    search_query = request.GET.get("search", "").strip()
    status_filter = request.GET.get("status", "").strip()
    org_filter_pk = request.GET.get("organization", "").strip()

    if search_query:
        sessions_queryset = sessions_queryset.filter(
            Q(title__icontains=search_query) | Q(description__icontains=search_query)
        )

    if status_filter:
        sessions_queryset = sessions_queryset.filter(status=status_filter)

    if org_filter_pk:
        if org_filter_pk == "personal":
            sessions_queryset = sessions_queryset.filter(organization=None)
        else:
            sessions_queryset = sessions_queryset.filter(organization__pk=org_filter_pk)

    total_sessions = sessions_queryset.count()
    open_sessions = sessions_queryset.filter(status="Open").count()
    closed_sessions = sessions_queryset.filter(status="Closed").count()

    return render(
        request,
        "session_list.html",
        {
            "sessions": sessions_queryset,
            "total_sessions": total_sessions,
            "open_sessions": open_sessions,
            "closed_sessions": closed_sessions,
            "user_job_title": user_job_title,
            "org_filter_choices": org_filter_choices,
            "current_status_filter": status_filter,
            "current_org_filter": org_filter_pk,
            "current_search_query": search_query,
            "status_choices": [("Open", "Open"), ("Closed", "Closed")],
        },
    )


@login_required
def create_session_view(request):
    """Create a session (and related SessionSetting / AccessRule)."""
    if request.method == "POST":
        form = SessionForm(request.POST, user=request.user)
        if form.is_valid():
            organization = form.cleaned_data.get("organization")

            if organization:
                session_count = Session.objects.filter(
                    organization=organization
                ).count()
                if session_count >= organization.session_limit:
                    return redirect("choose_plan")

            session = form.save(commit=False)
            session.creator = request.user

            schedule_choice = form.cleaned_data.get("schedule_opening")
            session.status = "Open" if schedule_choice == "now" else "Scheduled"
            session.save()

            qr_type_choice = form.cleaned_data.get("qr_type")
            is_location_required = form.cleaned_data.get("is_location_required", False)
            check_in_window_minutes = (
                form.cleaned_data.get("check_in_window_minutes") or 0
            )

            SessionSetting.objects.update_or_create(
                session=session,
                defaults={
                    "is_dynamic_qr": (qr_type_choice == "dynamic"),
                    "is_location_required": is_location_required,
                    "check_in_window_minutes": check_in_window_minutes,
                },
            )

            if schedule_choice and str(schedule_choice).isdigit():
                run_at = timezone.now() + timedelta(seconds=int(schedule_choice))
                open_session_task(session.pk, schedule=run_at)

            access_type = form.cleaned_data.get("access_type")
            if access_type == "private":
                email_domain = form.cleaned_data.get("email_domain")
                AccessRule.objects.create(
                    session=session, rule_type="EMAIL_DOMAIN", rule_value=email_domain
                )

            return redirect("dashboard")
    else:
        form = SessionForm(user=request.user)

    return render(request, "create_session.html", {"form": form})


@login_required
def session_detail_view(request, pk):
    """
    Session details + manual actions + static QR generation.
    """
    try:
        session = Session.objects.get(
            Q(
                organization__in=request.user.organizations.filter(
                    organizationmember__status="active"
                )
            )
            | Q(creator=request.user, organization=None),
            pk=pk,
        )
    except Session.DoesNotExist:
        return redirect("dashboard")

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "open":
            session.status = "Open"
            session.save()

        elif action == "close":
            session.status = "Closed"
            session.save()

        elif action == "add_manual":
            email = request.POST.get("email")
            name = request.POST.get("name")

            if email and name:
                user, _created = User.objects.get_or_create(
                    email=email,
                    defaults={
                        "first_name": name,
                        "last_name": "",
                        "sso_provider": "Manual",
                    },
                )

                AttendanceRecord.objects.get_or_create(
                    session=session,
                    user=user,
                    defaults={
                        "check_in_method": "Manual",
                        "is_verified": True,
                        "device_ip": "N/A",
                    },
                )

        elif action == "remove_attendee":
            record_id = request.POST.get("record_id")
            try:
                record = AttendanceRecord.objects.get(pk=record_id, session=session)
                record.delete()
            except AttendanceRecord.DoesNotExist:
                pass

        return redirect("session_detail", pk=session.pk)

    session_setting, _created = SessionSetting.objects.get_or_create(session=session)

    attendance_code, _created = AttendanceCode.objects.get_or_create(
        session=session,
        defaults={
            "static_qr_string": f"QRTendify|{pk}|{uuid.uuid4()}",
            "verification_number": str(random.randint(1000, 9999)).zfill(4),
        },
    )

    static_attendance_url = (
        reverse("attendance_form") + f"?code={attendance_code.static_qr_string}"
    )
    qr_data_string = request.build_absolute_uri(static_attendance_url)

    qr_img = qrcode.make(qr_data_string)
    buf = io.BytesIO()
    qr_img.save(buf, format="PNG")
    qr_image_base64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    qr_data_uri = f"data:image/png;base64,{qr_image_base64}"

    attendees = (
        AttendanceRecord.objects.filter(session=session)
        .select_related("user", "devicelog")
        .order_by("-check_in_time")
    )

    return render(
        request,
        "session_detail.html",
        {
            "session": session,
            "attendance_code": attendance_code,
            "qr_data_uri": qr_data_uri,
            "static_qr_url": qr_data_string,
            "attendees": attendees,
            "session_setting": session_setting,
        },
    )


class SessionUpdateView(UpdateView):
    """Edit an existing session and its related settings."""

    model = Session
    form_class = SessionEditForm
    template_name = "session_edit.html"

    def get_queryset(self):
        return sessions_user_can_access(self.request.user)

    def get_initial(self):
        initial = super().get_initial()
        session = self.get_object()

        try:
            setting = SessionSetting.objects.get(session=session)
            initial["qr_type"] = "dynamic" if setting.is_dynamic_qr else "static"
            initial["is_location_required"] = setting.is_location_required
            initial["check_in_window_minutes"] = setting.check_in_window_minutes
        except SessionSetting.DoesNotExist:
            initial["qr_type"] = "static"
            initial["is_location_required"] = False
            initial["check_in_window_minutes"] = 0

        try:
            rule = AccessRule.objects.get(session=session, rule_type="EMAIL_DOMAIN")
            initial["access_type"] = "private"
            initial["email_domain"] = rule.rule_value
        except AccessRule.DoesNotExist:
            initial["access_type"] = "public"

        return initial

    def form_valid(self, form):
        session = form.save()

        qr_type_choice = form.cleaned_data.get("qr_type")
        is_location_required = form.cleaned_data.get("is_location_required", False)
        check_in_window_minutes = form.cleaned_data.get("check_in_window_minutes") or 0

        SessionSetting.objects.update_or_create(
            session=session,
            defaults={
                "is_dynamic_qr": (qr_type_choice == "dynamic"),
                "qr_refresh_interval_seconds": 120,
                "is_location_required": is_location_required,
                "check_in_window_minutes": check_in_window_minutes,
            },
        )

        access_type = form.cleaned_data.get("access_type")
        if access_type == "private":
            email_domain = form.cleaned_data.get("email_domain")
            AccessRule.objects.update_or_create(
                session=session,
                rule_type="EMAIL_DOMAIN",
                defaults={"rule_value": email_domain},
            )
        else:
            AccessRule.objects.filter(session=session).delete()

        schedule_choice = form.cleaned_data.get("schedule_opening")
        if schedule_choice == "now":
            session.status = "Open"
            session.save()
        elif schedule_choice and str(schedule_choice).isdigit():
            run_at = timezone.now() + timedelta(seconds=int(schedule_choice))
            open_session_task(session.pk, schedule=run_at)

        return super().form_valid(form)

    def get_success_url(self):
        next_url = self.request.GET.get("next")
        if next_url:
            return next_url
        return reverse("session_detail", kwargs={"pk": self.object.pk})


@login_required
def session_delete_view(request, pk):
    """Delete a session."""
    try:
        session = Session.objects.get(pk=pk)
        if not user_can_access_session(request.user, session):
            return redirect("dashboard")
    except Session.DoesNotExist:
        return redirect("dashboard")

    if request.method == "POST":
        session.delete()
        return redirect("dashboard")

    return redirect("session_edit", pk=pk)
