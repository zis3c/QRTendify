from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.template.defaultfilters import date as _date_format

from ..models import AttendanceRecord, Session, SessionSetting
from ..services.session_access import user_can_access_session


@login_required
def api_get_attendees_view(request, pk):
    """Get attendee list for live updates."""
    try:
        session = Session.objects.get(pk=pk)
    except Session.DoesNotExist:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    if not user_can_access_session(request.user, session):
        return JsonResponse({"error": "Unauthorized"}, status=403)

    attendees = (
        AttendanceRecord.objects.filter(session=session)
        .select_related("user", "devicelog")
        .order_by("-check_in_time")
    )

    try:
        session_setting = SessionSetting.objects.get(session=session)
        is_location_required = session_setting.is_location_required
    except SessionSetting.DoesNotExist:
        is_location_required = False

    attendee_list = []
    for index, record in enumerate(attendees):
        location_data = "N/A"
        google_maps_url = ""

        if (
            is_location_required
            and record.devicelog
            and record.devicelog.latitude is not None
        ):
            latitude_str = f"{record.devicelog.latitude:.4f}"
            longitude_str = f"{record.devicelog.longitude:.4f}"
            location_data = f"{latitude_str}, {longitude_str}"
            google_maps_url = f"http://maps.google.com/maps?q={record.devicelog.latitude},{record.devicelog.longitude}"

        attendee_list.append(
            {
                "id": record.id,
                "count": index + 1,
                "full_name": f"{record.user.first_name} {record.user.last_name}",
                "email": record.user.email,
                "check_in_time": _date_format(record.check_in_time, "N. j, Y, P"),
                "ip_address": record.device_ip,
                "location": location_data,
                "google_maps_url": google_maps_url,
            }
        )

    return JsonResponse(
        {"attendees": attendee_list, "is_location_required": is_location_required}
    )


@login_required
def api_get_attendance_status_view(request, pk):
    """Get attendance count and last submission time."""
    try:
        session = Session.objects.get(pk=pk)
    except Session.DoesNotExist:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    if not user_can_access_session(request.user, session):
        return JsonResponse({"error": "Unauthorized"}, status=403)

    records = AttendanceRecord.objects.filter(session=session)
    attendee_count = records.count()
    last_submission = records.order_by("-check_in_time").first()
    last_submission_timestamp = (
        last_submission.check_in_time if last_submission else None
    )

    return JsonResponse(
        {
            "attendee_count": attendee_count,
            "last_submission_timestamp": last_submission_timestamp,
        }
    )
