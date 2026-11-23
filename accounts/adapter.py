from allauth.account.adapter import DefaultAccountAdapter
from django.urls import reverse

from team.permissions import is_team_member


class AccountAdapter(DefaultAccountAdapter):
    """After login, team members land in the team area; customers on their profile."""

    def get_login_redirect_url(self, request):
        if is_team_member(request.user):
            return reverse("team:hub")
        return super().get_login_redirect_url(request)
