from django import forms

from ..models import Organization, Session

ACCESS_CHOICES = [
    ("public", "Public (Any email can attend)"),
    ("private", "Private (Restricted by email domain)"),
]
QR_TYPE_CHOICES = [
    ("static", "Static QR Code"),
    ("dynamic", "Dynamic QR Code"),
]
SCHEDULE_CHOICES = [
    ("now", "Open Immediately (Default)"),
    (300, "Open in 5 Minutes"),
    (600, "Open in 10 Minutes"),
    (1800, "Open in 30 Minutes"),
]
STATUS_CHOICES = [
    ("Scheduled", "Scheduled"),
    ("Open", "Open"),
    ("Closed", "Closed"),
]


class _EmailDomainValidationMixin:
    """Shared validation for access_type / email_domain fields."""

    def clean(self):
        cleaned_data = super().clean()
        access_type = cleaned_data.get("access_type")
        email_domain = cleaned_data.get("email_domain")

        if access_type == "private":
            if not email_domain:
                self.add_error(
                    "email_domain",
                    "This field is required when access is set to Private.",
                )
            elif not email_domain.startswith("@"):
                self.add_error(
                    "email_domain", "Domain must start with '@' (e.g., @school.edu)"
                )

        return cleaned_data


class SessionForm(_EmailDomainValidationMixin, forms.ModelForm):
    """Form for creating a new session."""

    organization = forms.ModelChoiceField(
        queryset=Organization.objects.none(),
        label="Assign to Organization (optional)",
        required=False,
        empty_label="Personal session (no organization)",
    )

    start_time = forms.DateTimeField(
        widget=forms.DateTimeInput(
            attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
        )
    )
    end_time = forms.DateTimeField(
        widget=forms.DateTimeInput(
            attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
        )
    )

    qr_type = forms.ChoiceField(
        choices=QR_TYPE_CHOICES, initial="static", label="QR Code Type"
    )
    is_location_required = forms.BooleanField(
        required=False,
        label="Require Location Verification?",
        widget=forms.CheckboxInput(attrs={"class": "custom-checkbox-toggle"}),
        help_text="If checked, attendees must provide their location during attendance.",
    )
    check_in_window_minutes = forms.IntegerField(
        required=False,
        min_value=0,
        initial=0,
        label="Check-in Grace Period (Minutes)",
        help_text="Duration after the Start Time when check-ins are still accepted. 0 = no time limit.",
    )

    schedule_opening = forms.ChoiceField(
        choices=SCHEDULE_CHOICES, initial="now", label="Scheduled Opening"
    )

    access_type = forms.ChoiceField(
        choices=ACCESS_CHOICES, initial="public", label="Access Control"
    )
    email_domain = forms.CharField(
        label="Allowed Email Domain",
        required=False,
        help_text="Required if access is 'Private'. Must start with '@' (e.g., @school.edu)",
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        self.fields["title"].widget.attrs["placeholder"] = "Enter session title"
        self.fields["description"].widget.attrs["placeholder"] = (
            "Add a short description (optional)"
        )
        self.fields["description"].widget.attrs["rows"] = 3

        if not user:
            return

        orgs = (
            Organization.objects.filter(
                organizationmember__user=user,
                organizationmember__status="active",
            )
            .prefetch_related("organizationmember_set")
            .distinct()
        )

        self.fields["organization"].queryset = orgs

        def label_for_org(org: Organization) -> str:
            is_owner = org.organizationmember_set.filter(
                user=user, role="Owner"
            ).exists()
            return f"{org.name} (Personal Session)" if is_owner else org.name

        self.fields["organization"].label_from_instance = label_for_org  # type: ignore[attr-defined]

    class Meta:
        model = Session
        fields = ["organization", "title", "description", "start_time", "end_time"]


class SessionEditForm(_EmailDomainValidationMixin, forms.ModelForm):
    """Edit an existing session, including related model fields."""

    status = forms.ChoiceField(choices=STATUS_CHOICES, label="Session Status")
    start_time = forms.DateTimeField(
        widget=forms.DateTimeInput(
            attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
        )
    )
    end_time = forms.DateTimeField(
        widget=forms.DateTimeInput(
            attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
        )
    )

    qr_type = forms.ChoiceField(choices=QR_TYPE_CHOICES, label="QR Code Type")
    is_location_required = forms.BooleanField(
        required=False,
        label="Require Location Verification?",
        widget=forms.CheckboxInput(attrs={"class": "custom-checkbox-toggle"}),
        help_text="If checked, attendees must provide their location during attendance.",
    )

    schedule_opening = forms.ChoiceField(
        choices=SCHEDULE_CHOICES,
        initial="now",
        label="Scheduled Opening",
        required=False,
    )

    access_type = forms.ChoiceField(choices=ACCESS_CHOICES, label="Access Control")
    email_domain = forms.CharField(
        label="Allowed Email Domain",
        required=False,
        help_text="Required if access is 'Private'. Must start with '@' (e.g., @school.edu)",
    )

    class Meta:
        model = Session
        fields = ["title", "description", "status", "start_time", "end_time"]
