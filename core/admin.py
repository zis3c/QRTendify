from django.contrib import admin
from django.db.models import Count
from django.urls import path
from django.shortcuts import render
from django.contrib.admin.models import LogEntry
from import_export import resources
from import_export.admin import ImportExportModelAdmin, ImportExportActionModelAdmin
from simple_history.admin import SimpleHistoryAdmin
from . import models

# Try to import guardian and adminactions with error handling
try:
    from guardian.admin import GuardedModelAdmin

    GUARDIAN_AVAILABLE = True
except ImportError:
    GUARDIAN_AVAILABLE = False

    class GuardedModelAdmin(admin.ModelAdmin):
        pass


try:
    import adminactions.actions as actions

    ADMINACTIONS_AVAILABLE = True
except ImportError:
    ADMINACTIONS_AVAILABLE = False

# --- IMPORT-EXPORT RESOURCES ---


class UserResource(resources.ModelResource):
    class Meta:
        model = models.User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "sso_provider",
            "job_title",
            "is_active",
            "date_joined",
        )
        export_order = fields


class SessionResource(resources.ModelResource):
    class Meta:
        model = models.Session
        fields = (
            "id",
            "title",
            "organization__name",
            "creator__email",
            "status",
            "start_time",
            "end_time",
            "created_at",
        )
        export_order = fields


class OrganizationResource(resources.ModelResource):
    class Meta:
        model = models.Organization
        fields = ("id", "name", "domain", "plan__name", "session_limit", "created_at")
        export_order = fields


class AttendanceRecordResource(resources.ModelResource):
    class Meta:
        model = models.AttendanceRecord
        fields = (
            "id",
            "session__title",
            "user__email",
            "user__first_name",
            "user__last_name",
            "check_in_time",
            "check_in_method",
            "device_ip",
        )
        export_order = fields


# --- ENHANCED ADMIN CLASSES ---


class UserAdmin(ImportExportActionModelAdmin, SimpleHistoryAdmin, GuardedModelAdmin):
    resource_class = UserResource
    list_display = (
        "email",
        "first_name",
        "last_name",
        "sso_provider",
        "job_title",
        "is_active",
        "date_joined",
    )
    list_filter = ("sso_provider", "is_active", "date_joined")
    search_fields = ("email", "first_name", "last_name")
    history_list_display = ["email", "is_active"]
    actions = ["activate_users", "deactivate_users"]

    def activate_users(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} users activated successfully.")

    activate_users.short_description = "Activate selected users"

    def deactivate_users(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} users deactivated successfully.")

    deactivate_users.short_description = "Deactivate selected users"


class SessionAdmin(ImportExportActionModelAdmin, SimpleHistoryAdmin):
    resource_class = SessionResource
    list_display = (
        "title",
        "organization",
        "creator",
        "status",
        "start_time",
        "attendee_count",
        "created_at",
    )
    list_filter = ("status", "organization", "created_at")
    search_fields = ("title", "description", "creator__email")
    history_list_display = ["status", "start_time"]
    actions = ["open_sessions", "close_sessions"]

    def attendee_count(self, obj):
        return obj.attendancerecord_set.count()

    attendee_count.short_description = "Attendees"

    def open_sessions(self, request, queryset):
        updated = queryset.update(status="Open")
        self.message_user(request, f"{updated} sessions opened successfully.")

    open_sessions.short_description = "Open selected sessions"

    def close_sessions(self, request, queryset):
        updated = queryset.update(status="Closed")
        self.message_user(request, f"{updated} sessions closed successfully.")

    close_sessions.short_description = "Close selected sessions"


class OrganizationAdmin(ImportExportActionModelAdmin, SimpleHistoryAdmin):
    resource_class = OrganizationResource
    list_display = (
        "name",
        "domain",
        "plan",
        "session_limit",
        "member_count",
        "created_at",
    )
    list_filter = ("plan", "created_at")
    search_fields = ("name", "domain")
    history_list_display = ["name", "session_limit"]

    def member_count(self, obj):
        return obj.organizationmember_set.count()

    member_count.short_description = "Members"


class AttendanceRecordAdmin(ImportExportActionModelAdmin, SimpleHistoryAdmin):
    resource_class = AttendanceRecordResource
    list_display = (
        "user",
        "session",
        "check_in_time",
        "check_in_method",
        "device_ip",
        "has_location",
    )
    list_filter = ("check_in_method", "check_in_time", "session")
    search_fields = (
        "user__email",
        "user__first_name",
        "user__last_name",
        "session__title",
    )
    date_hierarchy = "check_in_time"

    def has_location(self, obj):
        return "✅" if hasattr(obj, "devicelog") and obj.devicelog else "❌"

    has_location.short_description = "Location"


class PlanAdmin(ImportExportModelAdmin, SimpleHistoryAdmin):
    list_display = ("plan_id", "name", "session_limit", "price")
    list_editable = ("session_limit", "price")


class AttendanceCodeAdmin(SimpleHistoryAdmin):
    list_display = ("session", "verification_number")
    search_fields = ("session__title", "verification_number")


class AccessRuleAdmin(SimpleHistoryAdmin):
    list_display = ("session", "rule_type", "rule_value", "is_allow_list")
    list_filter = ("rule_type", "is_allow_list")


class DeviceLogAdmin(SimpleHistoryAdmin):
    list_display = ("attendance_record", "latitude", "longitude")
    list_filter = ("attendance_record__session",)


class SessionSettingAdmin(SimpleHistoryAdmin):
    list_display = ("session", "is_dynamic_qr", "is_location_required")
    list_editable = ("is_dynamic_qr", "is_location_required")


class OrganizationMemberAdmin(SimpleHistoryAdmin):
    list_display = ("organization", "user", "role", "status")
    list_filter = ("role", "status", "organization")
    list_editable = ("role", "status")
    actions = ["activate_members", "deactivate_members"]

    def activate_members(self, request, queryset):
        updated = queryset.update(status="active")
        self.message_user(request, f"{updated} members activated successfully.")

    activate_members.short_description = "Activate selected members"

    def deactivate_members(self, request, queryset):
        updated = queryset.update(status="pending")
        self.message_user(request, f"{updated} members deactivated successfully.")

    deactivate_members.short_description = "Deactivate selected members"


class DynamicQrTokenAdmin(admin.ModelAdmin):
    list_display = ("session", "verification_code", "expires_at", "created_at")
    list_filter = ("expires_at", "created_at")
    readonly_fields = ("token", "created_at")


# --- CUSTOM ADMIN SITE ---


class QRTendifyAdmin(admin.AdminSite):
    site_header = "🚀 QRTendify Enhanced Administration"
    site_title = "QRTendify Admin Pro"
    index_title = "Analytics Dashboard & Management"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "analytics/",
                self.admin_view(self.analytics_view),
                name="analytics-dashboard",
            ),
        ]
        return custom_urls + urls

    def analytics_view(self, request):
        total_users = models.User.objects.count()
        total_orgs = models.Organization.objects.count()
        total_sessions = models.Session.objects.count()
        sessions_status = models.Session.objects.values("status").annotate(
            count=Count("id")
        )
        sessions_status_dict = {
            item["status"]: item["count"] for item in sessions_status
        }
        active_memberships = models.OrganizationMember.objects.filter(
            status="active"
        ).count()
        pending_memberships = models.OrganizationMember.objects.filter(
            status="pending"
        ).count()
        social_users = models.User.objects.exclude(sso_provider="").count()
        manual_users = models.User.objects.filter(sso_provider="").count()
        recent_activity = LogEntry.objects.select_related(
            "user", "content_type"
        ).order_by("-action_time")[:10]

        context = {
            **self.each_context(request),
            "total_users": total_users,
            "total_orgs": total_orgs,
            "total_sessions": total_sessions,
            "sessions_status": sessions_status_dict,
            "active_memberships": active_memberships,
            "pending_memberships": pending_memberships,
            "social_users": social_users,
            "manual_users": manual_users,
            "recent_activity": recent_activity,
        }
        return render(request, "admin/analytics_dashboard.html", context)

    def index(self, request, extra_context=None):
        if extra_context is None:
            extra_context = {}
        extra_context.update(
            {
                "total_users": models.User.objects.count(),
                "total_orgs": models.Organization.objects.count(),
                "total_sessions": models.Session.objects.count(),
            }
        )
        return super().index(request, extra_context=extra_context)


# Instantiate enhanced admin site
qrtendify_admin_site = QRTendifyAdmin()

# Register all models with the custom admin site
qrtendify_admin_site.register(models.User, UserAdmin)
qrtendify_admin_site.register(models.Session, SessionAdmin)
qrtendify_admin_site.register(models.Organization, OrganizationAdmin)
qrtendify_admin_site.register(models.AttendanceRecord, AttendanceRecordAdmin)
qrtendify_admin_site.register(models.Plan, PlanAdmin)
qrtendify_admin_site.register(models.AttendanceCode, AttendanceCodeAdmin)
qrtendify_admin_site.register(models.AccessRule, AccessRuleAdmin)
qrtendify_admin_site.register(models.DeviceLog, DeviceLogAdmin)
qrtendify_admin_site.register(models.SessionSetting, SessionSettingAdmin)
qrtendify_admin_site.register(models.OrganizationMember, OrganizationMemberAdmin)
qrtendify_admin_site.register(models.DynamicQrToken, DynamicQrTokenAdmin)

# Add adminactions if available
if ADMINACTIONS_AVAILABLE:
    try:
        actions.add_to_site(qrtendify_admin_site)
    except Exception:
        pass

# Replace the default admin site
admin.site = qrtendify_admin_site
