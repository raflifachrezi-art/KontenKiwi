# Copyright (c) 2019-2026 Alexander Todorov <atodorov@MrSenko.com>

# Licensed under the GPL 2.0: https://www.gnu.org/licenses/old-licenses/gpl-2.0.html


from django.contrib.auth.decorators import permission_required
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView
from django.views.generic.base import TemplateView, View
from django.views.generic.edit import CreateView, UpdateView
from guardian.decorators import permission_required as object_permission_required

from tcms.bugs.forms import BugCommentForm, NewBugForm
from tcms.bugs.models import Bug, BugStatus
from tcms.core.helpers.comments import add_comment
from tcms.issuetracker.monday import Monday
from tcms.management.models import Component
from tcms.testcases.models import BugSystem


@method_decorator(
    object_permission_required(
        "bugs.view_bug", (Bug, "pk", "pk"), accept_global_perms=True
    ),
    name="dispatch",
)
class Get(DetailView):
    model = Bug
    template_name = "bugs/get.html"
    http_method_names = ["get"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["comment_form"] = BugCommentForm(initial={"status_code": self.object.status_code})
        context["comment_form"].populate(self.object.pk)
        context["bug_statuses"] = BugStatus.choices
        context["executions"] = self.object.executions.all()
        context["OBJECT_MENU_ITEMS"] = [
            (
                "...",
                [
                    (_("Edit"), reverse("bugs-edit", args=[self.object.pk])),
                    ("-", "-"),
                    (
                        _("Object permissions"),
                        reverse("admin:bugs_bug_permissions", args=[self.object.pk]),
                    ),
                    ("-", "-"),
                    (
                        _("Delete"),
                        reverse("admin:bugs_bug_delete", args=[self.object.pk]),
                    ),
                ],
            )
        ]

        return context


@method_decorator(permission_required("bugs.add_bug"), name="dispatch")
class New(CreateView):
    model = Bug
    form_class = NewBugForm
    template_name = "bugs/mutable.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = _("New Bug")
        context["form_post_url"] = reverse("bugs-new")
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["initial"].update(  # pylint: disable=objects-update-used
            {
                "reporter": self.request.user,
            }
        )
        kwargs["request"] = self.request
        return kwargs

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # clear fields which are set dynamically via JavaScript
        form.populate(self.request.POST.get("product", -1))
        return form

    def form_valid(self, form):
        response = super().form_valid(form)

        if not self.object.assignee:
            self.object.assignee = New.find_assignee(self.request.POST)
            self.object.save()
        add_comment([self.object], form.cleaned_data["text"], self.request.user)

        return response

    @staticmethod
    def assignee_from_components(components):
        """
        Return the first owner which is assigned to any of the
        components. This is as best as we can to automatically figure
        out who should be assigned to this bug.
        """
        for component in components:
            if component.initial_owner:
                return component.initial_owner

        return None

    @staticmethod
    def find_assignee(data):
        """
        Try to automatically find an assignee for Bug by first scanning
        TestCase components (if present) and then components for the
        product.
        """
        assignee = None
        if "_execution" in data:
            assignee = New.assignee_from_components(
                data["_execution"].case.component.all()
            )
            del data["_execution"]

        if not assignee:
            assignee = New.assignee_from_components(
                Component.objects.filter(product=data["product"])
            )

        return assignee

    @staticmethod
    def create_bug(data):
        """
        Helper method used within Issue Tracker integration.

        :param data: Untrusted input, usually via HTTP request
        :type data: dict
        :return: bug
        :rtype: Model
        """
        bug = None

        if "assignee" not in data or not data["assignee"]:
            data["assignee"] = New.find_assignee(data)

        text = data["text"]
        del data["text"]

        bug = Bug.objects.create(**data)
        add_comment([bug], text, bug.reporter)

        return bug


@method_decorator(
    object_permission_required(
        "bugs.change_bug", (Bug, "pk", "pk"), accept_global_perms=True
    ),
    name="dispatch",
)
class Edit(UpdateView):
    model = Bug
    form_class = NewBugForm
    template_name = "bugs/mutable.html"
    _values_before_update = {}

    def _record_changes(self, new_data):
        result = ""
        for field in self.model._meta.fields:
            field = field.name
            if (
                field in new_data
                and self._values_before_update[field] != new_data[field]
            ):
                _before_update = self._values_before_update[field]
                _after_update = new_data[field]
                result += f"{field.title()}: {_before_update} -> {_after_update}\n"
        if result:
            add_comment([self.object], result, self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def get_initial(self):
        return {
            "assignee": self.object.assignee,
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = _("Edit bug")
        context["form_post_url"] = reverse(
            "bugs-edit",
            args=[
                self.object.pk,
            ],
        )
        return context

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        for field in self.model._meta.fields:
            self._values_before_update[field.name] = getattr(obj, field.name)
        return obj

    def form_valid(self, form):
        self._record_changes(form.cleaned_data)
        return super().form_valid(form)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        if self.request.POST.get("product"):
            form.populate(product_id=self.request.POST["product"])
        else:
            form.populate(product_id=self.object.product_id)
        return form


@method_decorator(permission_required("django_comments.add_comment"), name="dispatch")
class AddComment(View):
    http_methods = ["post"]

    def post(self, request):  # pylint: disable=no-self-use
        form = BugCommentForm(request.POST)
        request_action = request.POST.get("action")

        if form.is_valid():
            bug = form.cleaned_data["bug"]
            if form.cleaned_data["text"]:
                add_comment([bug], form.cleaned_data["text"], request.user)

            new_status = request.POST.get("status_code") or form.cleaned_data.get("status_code")
            if request_action == "close":
                bug.status_code = BugStatus.CLOSED
                bug.status = False
                add_comment([bug], _("*bug closed*"), request.user)

            elif request_action == "reopen":
                bug.status_code = BugStatus.OPEN
                bug.status = True
                add_comment([bug], _("*bug reopened*"), request.user)

            elif new_status and new_status in BugStatus.values and new_status != bug.status_code:
                old_status = bug.status_code
                bug.status_code = new_status
                if new_status in [BugStatus.CLOSED, BugStatus.RESOLVED, BugStatus.WONT_FIX]:
                    bug.status = False
                else:
                    bug.status = True
                add_comment([bug], _(f"*status changed: {old_status} ➔ {new_status}*"), request.user)

            bug.save()

            return HttpResponseRedirect(reverse("bugs-get", args=[bug.pk]))

        return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))


@method_decorator(permission_required("bugs.view_bug"), name="dispatch")
class Search(TemplateView):
    template_name = "bugs/search.html"

    def get_context_data(self, **kwargs):
        form = NewBugForm(self.request.GET)
        form.populate(self.request.GET.get("product", -1))

        return {"form": form}


@method_decorator(permission_required("bugs.change_bug"), name="dispatch")
class PushToMonday(View):
    def post(self, request, pk):
        bug = Bug.objects.get(pk=pk)
        bug_system = BugSystem.objects.filter(
            tracker_type__icontains="Monday"
        ).first()
        if not bug_system:
            bug_system, _ = BugSystem.objects.get_or_create(
                name="Monday.com (Konten)",
                defaults={
                    "base_url": "https://konten.monday.com",
                    "tracker_type": "tcms.issuetracker.monday.Monday",
                    "description": "Monday.com Development Timeline",
                },
            )
        tracker = Monday(bug_system, request)
        if not tracker.api_token:
            messages.add_message(
                request,
                messages.ERROR,
                _(
                    "Token Monday.com belum diatur di profil Anda. Silakan isi token di tab Integrasi Monday.com pada profil Anda."
                ),
            )
            return HttpResponseRedirect(reverse("tcms-profile", args=[request.user.pk]))

        try:
            res = tracker.push_bug_to_monday(bug, request.user)
            add_comment(
                [bug],
                f"*Bug ditautkan ke Monday.com Subitem #{res['subitem_id']} ({res['phase']}, Owner: {res['owner'] or 'None'})*",
                request.user,
            )
            messages.add_message(
                request,
                messages.SUCCESS,
                _(f"Berhasil menautkan ke Monday.com Subitem #{res['subitem_id']}"),
            )
        except Exception as exc:
            messages.add_message(
                request,
                messages.ERROR,
                _(f"Gagal push ke Monday.com: {str(exc)}"),
            )

        return HttpResponseRedirect(reverse("bugs-get", args=[bug.pk]))


@method_decorator(permission_required("bugs.change_bug"), name="dispatch")
class SyncFromMonday(View):
    def post(self, request, pk):
        bug = Bug.objects.get(pk=pk)
        if bug.monday_url:
            bug_system = BugSystem.objects.filter(
                tracker_type__icontains="Monday"
            ).first()
            if not bug_system:
                bug_system, _ = BugSystem.objects.get_or_create(
                    name="Monday.com (Konten)",
                    defaults={
                        "base_url": "https://konten.monday.com",
                        "tracker_type": "tcms.issuetracker.monday.Monday",
                    },
                )
            tracker = Monday(bug_system, request)
            try:
                details = tracker.details(bug.monday_url)
                if details and details.get("status"):
                    old_status = bug.monday_status
                    bug.monday_status = details["status"]
                    bug.save()
                    messages.add_message(
                        request,
                        messages.SUCCESS,
                        _(
                            f"Status Monday.com berhasil disinkronkan: '{old_status}' ➔ '{details['status']}'"
                        ),
                    )
                else:
                    messages.add_message(
                        request,
                        messages.WARNING,
                        _("Status di Monday.com tidak berubah atau tidak ditemukan."),
                    )
            except Exception as exc:
                messages.add_message(
                    request,
                    messages.ERROR,
                    _(f"Gagal sinkronisasi dari Monday.com: {str(exc)}"),
                )
        return HttpResponseRedirect(reverse("bugs-get", args=[bug.pk]))

