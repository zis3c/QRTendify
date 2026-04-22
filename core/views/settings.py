"""User settings and QR token generation views."""

import random
import uuid
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic.edit import UpdateView

from ..forms import CustomUserChangeForm
from ..models import (
    DynamicQrToken,
    OrganizationMember,
    Session,
    User,
)
from ..services.session_access import user_can_access_session


class SettingsView(UpdateView):
    """Update current user's profile + manage pending invitations."""

    model = User
    form_class = CustomUserChangeForm
    template_name = "settings.html"
    success_url = reverse_lazy("dashboard")

    def get_object(self):
        return self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["invitations"] = (
            OrganizationMember.objects.filter(user=self.request.user, status="pending")
            .select_related("organization")
            .order_by("organization__name")
        )
        return context


@login_required
def generate_qr_token_view(request, pk):
    """Generate a new dynamic QR token and 4-digit manual code."""
    try:
        session = Session.objects.get(pk=pk)
        if not user_can_access_session(request.user, session):
            return JsonResponse({"error": "Unauthorized"}, status=403)
    except Session.DoesNotExist:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    token = uuid.uuid4().hex

    active_codes = set(
        DynamicQrToken.objects.filter(expires_at__gt=timezone.now()).values_list(
            "verification_code", flat=True
        )
    )

    manual_code = str(random.randint(1000, 9999)).zfill(4)
    while manual_code in active_codes:
        manual_code = str(random.randint(1000, 9999)).zfill(4)

    expires_at = timezone.now() + timedelta(minutes=2)

    DynamicQrToken.objects.filter(session=session).delete()
    DynamicQrToken.objects.create(
        session=session,
        token=token,
        verification_code=manual_code,
        expires_at=expires_at,
    )

    return JsonResponse(
        {
            "token": token,
            "expires_at": expires_at.isoformat(),
            "manual_code": manual_code,
        }
    )
