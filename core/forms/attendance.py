from django import forms


class AttendanceForm(forms.Form):
    """The form presented to attendees for check-in."""

    name = forms.CharField(label="Your Full Name", max_length=100)
    email = forms.EmailField(label="Email Address")
    latitude = forms.DecimalField(widget=forms.HiddenInput(), required=False)
    longitude = forms.DecimalField(widget=forms.HiddenInput(), required=False)


class CodeRedirectForm(forms.Form):
    """A simple form to accept a 4-digit code for attendance check-in."""

    code = forms.CharField(
        label="4-Digit Verification Code",
        max_length=4,
        widget=forms.TextInput(attrs={"placeholder": "1234"}),
    )
