"""Team area: who is on the team and with which roles (Shop Managers only)."""

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _

from ..forms import FindMemberForm, MemberRolesForm
from ..mixins import team_required
from ..permissions import ROLE_DESCRIPTIONS, ROLES, SHOP_MANAGER, Area, roles_of

User = get_user_model()


@team_required(Area.MEMBERS)
def member_list(request):
    members = (
        User.objects.filter(Q(is_superuser=True) | Q(groups__name__in=ROLES))
        .distinct()
        .prefetch_related("groups")
        .order_by("-is_superuser", "email")
    )
    form = FindMemberForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        return redirect("team:member_edit", pk=form.user.pk)
    context = {"members": members, "form": form, "role_descriptions": ROLE_DESCRIPTIONS.items()}
    return render(request, "team/member_list.html", context)


@team_required(Area.MEMBERS)
def member_edit(request, pk):
    member = get_object_or_404(User, pk=pk)
    if member.is_superuser:
        messages.info(
            request,
            _("%(email)s is an owner account (superuser) and can always do everything.") % {"email": member.email},
        )
        return redirect("team:members")

    current = roles_of(member)
    form = MemberRolesForm(request.POST or None, initial={"roles": current})
    if request.method == "POST" and form.is_valid():
        chosen = set(form.cleaned_data["roles"])
        if member == request.user and SHOP_MANAGER in current and SHOP_MANAGER not in chosen:
            messages.error(
                request, _("You can't remove your own Shop Manager role. Ask another Shop Manager to do it.")
            )
            return redirect("team:member_edit", pk=member.pk)

        member.groups.remove(*Group.objects.filter(name__in=ROLES))
        member.groups.add(*Group.objects.filter(name__in=chosen))
        if chosen:
            messages.success(
                request,
                _("%(email)s now has: %(roles)s.") % {"email": member.email, "roles": ", ".join(sorted(chosen))},
            )
        else:
            messages.success(request, _("%(email)s is no longer on the team.") % {"email": member.email})
        return redirect("team:members")

    return render(request, "team/member_form.html", {"member": member, "form": form})
