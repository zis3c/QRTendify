from allauth.account.adapter import DefaultAccountAdapter
from django.urls import reverse


class MyAccountAdapter(DefaultAccountAdapter):
    """
    Custom adapter to redirect users after login based on
    whether they have completed their organization setup.
    """

    def get_login_redirect_url(self, request):
        """
        Overrides the default redirect URL after login.
        """
        user = request.user

        # Check if the user is linked to ANY organization.
        # We check 'active' to ensure they don't skip this
        # if they have a 'pending' invite.
        if not user.organizations.filter(organizationmember__status="active").exists():
            return reverse("complete_profile")

        return reverse("dashboard")
