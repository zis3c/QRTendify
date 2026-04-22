from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from ..models import OrganizationMember, User


@login_required
def manage_organization_view(request):
    """Allows the owner to manage the organization's membership (invite/remove)."""
    membership = (
        OrganizationMember.objects.filter(user=request.user, status="active")
        .select_related("organization")
        .first()
    )

    if not membership:
        return redirect("settings")

    organization = membership.organization
    members = (
        OrganizationMember.objects.filter(organization=organization)
        .select_related("user")
        .order_by("status", "role", "user__email")
    )

    invite_error = None
    invite_success = None

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "invite_member":
            email = request.POST.get("email")
            try:
                user_to_invite = User.objects.get(email=email)
                is_already_member = OrganizationMember.objects.filter(
                    organization=organization, user=user_to_invite
                ).exists()

                if is_already_member:
                    invite_error = (
                        "This user is already a member of or has a pending invite "
                        "to your organization."
                    )
                else:
                    OrganizationMember.objects.create(
                        organization=organization,
                        user=user_to_invite,
                        role="Member",
                        status="pending",
                    )
                    invite_success = (
                        f"Success! An invitation has been sent to {email}. "
                        "They must log in to accept it."
                    )

            except User.DoesNotExist:
                invite_error = "User not found. Please ask them to register for a QRTendify account first."
            except Exception:
                invite_error = "An error occurred. This user might already be invited."

        elif action == "remove_member":
            member_id = request.POST.get("member_id")
            try:
                member_to_remove = OrganizationMember.objects.get(
                    pk=member_id, organization=organization
                )
                if member_to_remove.user != request.user:
                    member_to_remove.delete()
            except OrganizationMember.DoesNotExist:
                pass

            return redirect("manage_organization")

    context = {
        "organization": organization,
        "members": members,
        "invite_error": invite_error,
        "invite_success": invite_success,
    }
    return render(request, "manage_organization.html", context)
