from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.views.generic.base import RedirectView, TemplateView
from core.admin import qrtendify_admin_site
from django.conf import settings
from django.conf.urls.static import static

from core.views import (
    SessionUpdateView,
    SettingsView,
    dashboard_view,
    create_session_view,
    session_detail_view,
    reports_view,
    attendance_form_view,
    logout_view,
    landing_page_view,
    download_report_view,
    session_delete_view,
    choose_plan_view,
    generate_qr_token_view,
    attendance_success_view,
    download_attendance_proof_view,
    api_get_attendees_view,
    api_get_attendance_status_view,
    code_redirect_view,
    manage_organization_view,
    complete_profile_view,
    manage_invitation_view,
    delete_account_view,
    manual_signup_redirect_view,
    session_list_view,
    cancel_login_view,
)
from core.views import (
    certificate_list_view,
    certificate_detail_view,
    certificate_update_position_api,
    certificate_send_api,
)

app_name = "core"

urlpatterns = [
    # 1. PUBLIC & ANONYMOUS ACCESS
    path(
        "sw.js",
        TemplateView.as_view(
            template_name="sw.js", content_type="application/javascript"
        ),
        name="sw.js",
    ),
    path(
        "offline/", TemplateView.as_view(template_name="offline.html"), name="offline"
    ),
    path("", landing_page_view, name="landing_page"),
    path("attendance/", attendance_form_view, name="attendance_form"),
    path("attend-manual/", code_redirect_view, name="attend_manual"),
    path(
        "attendance/success/<int:record_id>/",
        attendance_success_view,
        name="attendance_success",
    ),
    path(
        "proof/<int:record_id>/download/",
        download_attendance_proof_view,
        name="download_proof",
    ),
    # 2. CORE DASHBOARD & SESSIONS
    path("dashboard/", dashboard_view, name="dashboard"),
    path("sessions/", session_list_view, name="session_list"),
    path("session/create/", create_session_view, name="create_session"),
    path("session/<int:pk>/", session_detail_view, name="session_detail"),
    path("session/<int:pk>/edit/", SessionUpdateView.as_view(), name="session_edit"),
    path("session/<int:pk>/delete/", session_delete_view, name="session_delete"),
    path("reports/", reports_view, name="reports"),
    path("report/<int:pk>/download/", download_report_view, name="download_report"),
    # 3. CERTIFICATE MANAGEMENT
    path("certificates/", certificate_list_view, name="certificate_list"),
    path(
        "certificates/session/<int:session_id>/",
        certificate_detail_view,
        name="certificate_detail",
    ),
    path(
        "certificates/api/update-position/<int:template_id>/",
        certificate_update_position_api,
        name="certificate_update_position",
    ),
    path(
        "certificates/api/send/<int:session_id>/",
        certificate_send_api,
        name="certificate_send_api",
    ),
    # 4. SETTINGS, ORGANIZATION & ACCOUNT MANAGEMENT
    path("settings/", SettingsView.as_view(), name="settings"),
    path("organization/manage/", manage_organization_view, name="manage_organization"),
    path("invitation/manage/", manage_invitation_view, name="manage_invitation"),
    path("account/delete/", delete_account_view, name="delete_account"),
    path("choose-plan/", choose_plan_view, name="choose_plan"),
    # 5. API ENDPOINTS
    path(
        "api/session/<int:pk>/attendees/",
        api_get_attendees_view,
        name="api_get_attendees",
    ),
    path(
        "api/session/<int:pk>/status/",
        api_get_attendance_status_view,
        name="api_get_attendance_status",
    ),
    path(
        "api/session/<int:pk>/generate-token/",
        generate_qr_token_view,
        name="api_generate_token",
    ),
    # 6. AUTHENTICATION (ALLAUTH & CUSTOM)
    path("secure-admin/", qrtendify_admin_site.urls, name="admin"),
    path("admin/", RedirectView.as_view(url="/secure-admin/", permanent=False)),
    path("accounts/", include("allauth.urls")),
    path(
        "manual-signup-redirect/",
        manual_signup_redirect_view,
        name="manual_signup_redirect",
    ),
    path("setup/organization/", complete_profile_view, name="complete_profile"),
    path(
        "register/",
        RedirectView.as_view(pattern_name="account_signup", permanent=False),
        name="register",
    ),
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="login.html", redirect_authenticated_user=True
        ),
        name="login",
    ),
    path("login/cancel/", cancel_login_view, name="cancel_login"),
    path("logout/", logout_view, name="logout"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
