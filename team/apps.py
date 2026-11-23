from django.apps import AppConfig
from django.db.models.signals import post_migrate


def create_role_groups(sender, **kwargs):
    """After every `migrate`, make sure each role in permissions.ROLES exists as a Group."""
    from django.contrib.auth.models import Group

    from .permissions import ROLES

    for name in ROLES:
        Group.objects.get_or_create(name=name)


class TeamConfig(AppConfig):
    name = "team"
    verbose_name = "Team area"

    def ready(self):
        # The team app has no models, so Django never sends post_migrate for it;
        # hook onto the auth app's signal instead (sent once the Group table exists).
        from django.apps import apps

        auth_app = apps.get_app_config("auth")
        post_migrate.connect(create_role_groups, sender=auth_app, dispatch_uid="team.create_role_groups")
