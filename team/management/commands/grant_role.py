"""
Give (or take away) a team role from the terminal — useful for the very
first Shop Manager, before anyone can use /team/members/.

    python manage.py grant_role ana@example.com "Shop Manager"
    python manage.py grant_role ana@example.com "Fulfilment" --remove
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError

from team.permissions import ROLES


class Command(BaseCommand):
    help = "Give a team role to a user (or remove it with --remove)."

    def add_arguments(self, parser):
        parser.add_argument("email")
        parser.add_argument("role", choices=list(ROLES))
        parser.add_argument("--remove", action="store_true", help="Take the role away instead.")

    def handle(self, email, role, remove, **options):
        user = get_user_model().objects.filter(email__iexact=email).first()
        if user is None:
            raise CommandError(f"No user with the email {email}. They need to sign up first.")
        group, _created = Group.objects.get_or_create(name=role)
        if remove:
            user.groups.remove(group)
            self.stdout.write(self.style.SUCCESS(f"{email} no longer has the role “{role}”."))
        else:
            user.groups.add(group)
            self.stdout.write(self.style.SUCCESS(f"{email} now has the role “{role}”. They can open /team/."))
