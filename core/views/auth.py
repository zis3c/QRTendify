from django.contrib import messages
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import redirect, render

from ..forms import OrganizationSetupForm
from ..models import Organization, OrganizationMember, Plan


@login_required
def manual_signup_redirect_view(request):
    if not request.user.organizations.filter(
        organizationmember__status="active"
    ).exists():
        return redirect("complete_profile")
    return redirect("dashboard")


@login_required
@transaction.atomic
def complete_profile_view(request):
    if request.user.organizations.exists():
        return redirect("dashboard")

    if request.method == "POST":
        form = OrganizationSetupForm(request.POST)
        if form.is_valid():
            user = request.user
            org_name = form.cleaned_data.get("organization_name")
            job_title = form.cleaned_data.get("job_title")

            user.job_title = job_title
            user.save()

            basic_plan, _created = Plan.objects.get_or_create(
                plan_id="BASIC",
                defaults={"name": "Basic Plan", "session_limit": 1, "price": 0.00},
            )

            organization = Organization.objects.create(
                name=org_name,
                domain=user.email.split("@")[-1],
                plan=basic_plan,
                session_limit=1,
            )

            OrganizationMember.objects.create(
                organization=organization,
                user=user,
                role="Owner",
                status="active",
            )

            return redirect("dashboard")
    else:
        form = OrganizationSetupForm()

    return render(request, "complete_profile.html", {"form": form})


def landing_page_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "landing.html")


def logout_view(request):
    auth_logout(request)
    messages.success(request, "Successfully signed out of your account.")
    return redirect("login")


def cancel_login_view(request):
    """
    Clears the potential partial session and redirects to login without
    showing the 'Signed out' success message.
    """
    auth_logout(request)
    return redirect("login")


@login_required
def manage_invitation_view(request):
    """Accept/decline action for a pending organization invitation."""
    if request.method == "POST":
        invite_id = request.POST.get("invite_id")
        action = request.POST.get("action")

        try:
            invite = OrganizationMember.objects.get(
                pk=invite_id, user=request.user, status="pending"
            )
        except OrganizationMember.DoesNotExist:
            invite = None

        if invite:
            if action == "accept":
                invite.status = "active"
                invite.save()
            elif action == "decline":
                invite.delete()

    return redirect("settings")


@login_required
@transaction.atomic
def delete_account_view(request):
    """
    Deletes the user and associated organizations if the user is the sole owner.
    """
    if request.method == "POST":
        user = request.user

        owned_memberships = OrganizationMember.objects.filter(user=user, role="Owner")
        for membership in owned_memberships:
            organization = membership.organization
            if organization.organizationmember_set.filter(role="Owner").count() == 1:
                organization.delete()

        auth_logout(request)
        user.delete()
        return redirect("landing_page")

    return render(request, "delete_account_confirm.html")
