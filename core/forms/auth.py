from allauth.account.forms import SignupForm
from django import forms
from django.contrib.auth.forms import UserChangeForm
from django.core.exceptions import ValidationError
from django.urls import reverse

from ..models import Organization, User

ROLE_CHOICES = [
    ("", "--- Select your role ---"),
    ("student", "Student"),
    ("lecturer", "Lecturer / Teacher"),
    ("admin", "Admin Staff"),
    ("manager", "Manager / Supervisor"),
    ("hr", "HR Officer"),
    ("security", "Security Officer"),
    ("organizer", "Event Organizer"),
    ("boss", "Boss"),
    ("croissant", "Croissant"),
    ("other", "Other"),
]


class CustomSignupForm(SignupForm):
    """Manual registration form adding First Name and Last Name."""

    first_name = forms.CharField(max_length=30, label="First Name", required=True)
    last_name = forms.CharField(max_length=30, label="Last Name", required=True)

    def save(self, request):
        user = super().save(request)
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.save()
        return user

    def get_signup_redirect_url(self, request):
        return reverse("complete_profile")


class CustomUserChangeForm(UserChangeForm):
    """Update a user's profile information."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].disabled = True

    class Meta:
        model = User
        fields = ("email", "first_name", "last_name")


class OrganizationSetupForm(forms.Form):
    """Used by new users to set up their initial organization."""

    organization_name = forms.CharField(
        max_length=100, required=True, label="Your Organization's Name"
    )
    job_title = forms.ChoiceField(
        choices=ROLE_CHOICES, required=True, label="What is your role?"
    )

    def clean_organization_name(self):
        org_name = self.cleaned_data.get("organization_name")
        if Organization.objects.filter(name=org_name).exists():
            raise ValidationError(
                "An organization with this name already exists. Please choose a different name."
            )
        return org_name
