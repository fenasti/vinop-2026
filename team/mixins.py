"""
Building blocks for the team area's create / edit / delete pages.

Every team view declares which `area` it belongs to:

    class WineCreateView(TeamCreateView):
        area = Area.CATALOG
        model = Wine
        form_class = WineForm
        list_url_name = "team:wines"

Not logged in → login page. Logged in without that area → 403 page.
"""

from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import ProtectedError
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.generic import CreateView, DeleteView, UpdateView

from .permissions import can

NO_ACCESS = "Your role doesn't include this part of the team area."


class TeamAccessMixin(LoginRequiredMixin):
    area = None  # set on every subclass

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not can(request.user, self.area):
            raise PermissionDenied(_(NO_ACCESS))
        return super().dispatch(request, *args, **kwargs)


def team_required(area):
    """The same check for function-based views: @team_required(Area.ORDERS)."""

    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(request, *args, **kwargs):
            if not can(request.user, area):
                raise PermissionDenied(_(NO_ACCESS))
            return view(request, *args, **kwargs)

        return wrapped

    return decorator


class TeamFormMixin(TeamAccessMixin):
    """Shared template, title and messages for create/edit pages."""

    template_name = "team/form.html"
    list_url_name = ""  # e.g. "team:wines": where Save and Cancel lead back to

    def get_success_url(self):
        return reverse(self.list_url_name)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = self.get_title()
        context["cancel_url"] = reverse(self.list_url_name)
        return context

    def form_invalid(self, form):
        messages.error(self.request, _("Please check the highlighted fields."))
        return super().form_invalid(form)


class TeamCreateView(TeamFormMixin, CreateView):
    def get_title(self):
        return _("New %(thing)s") % {"thing": self.model._meta.verbose_name}

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _("“%(object)s” is created.") % {"object": self.object})
        return response


class TeamUpdateView(TeamFormMixin, UpdateView):
    def get_title(self):
        return _("Edit “%(object)s”") % {"object": self.object}

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _("“%(object)s” is saved.") % {"object": self.object})
        return response


class TeamDeleteView(TeamAccessMixin, DeleteView):
    """Asks first, and explains instead of crashing when other records depend on it."""

    template_name = "team/confirm_delete.html"
    list_url_name = ""
    consequence = ""  # one sentence shown on the confirm page

    def get_success_url(self):
        return reverse(self.list_url_name)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["cancel_url"] = self.get_success_url()
        context["consequence"] = self.consequence
        context["verbose_name"] = self.model._meta.verbose_name
        return context

    def form_valid(self, form):
        name = str(self.object)
        try:
            self.object.delete()
        except ProtectedError as error:
            messages.error(
                self.request,
                _(
                    "“%(object)s” can't be deleted while %(count)d other record(s) still use it. "
                    "Move or delete those first."
                )
                % {"object": name, "count": len(error.protected_objects)},
            )
            return redirect(self.get_success_url())
        messages.success(self.request, _("“%(object)s” is deleted.") % {"object": name})
        return redirect(self.get_success_url())
