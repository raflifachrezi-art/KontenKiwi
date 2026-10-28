# Copyright (c) 2019-2022 Alexander Todorov <atodorov@MrSenko.com>

# Licensed under the GPL 2.0: https://www.gnu.org/licenses/old-licenses/gpl-2.0.html

from colorfield.fields import ColorField
from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from tcms.core.models.base import UrlMixin


class Severity(models.Model):
    name = models.CharField(max_length=64, unique=True)
    weight = models.IntegerField(default=0)
    icon = models.CharField(max_length=64)
    color = ColorField()

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = _("Severity")


class BugStatus(models.TextChoices):
    OPEN = "OPEN", _("Open")
    IN_PROGRESS = "IN_PROGRESS", _("In Progress")
    STUCK = "STUCK", _("Stuck")
    RESOLVED = "RESOLVED", _("Resolved")
    CLOSED = "CLOSED", _("Closed")
    WONT_FIX = "WONT_FIX", _("Won't Fix")


class Bug(models.Model, UrlMixin):
    summary = models.CharField(max_length=255, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    # True means bug is still open (kept for backward compatibility)
    status = models.BooleanField(default=True, db_index=True)
    status_code = models.CharField(
        max_length=32,
        choices=BugStatus.choices,
        default=BugStatus.OPEN,
        db_index=True,
    )

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="repoted_bugs"
    )
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="assigned_bugs",
        null=True,
        blank=True,
    )

    product = models.ForeignKey("management.Product", on_delete=models.CASCADE)
    version = models.ForeignKey("management.Version", on_delete=models.CASCADE)
    build = models.ForeignKey("management.Build", on_delete=models.CASCADE)
    severity = models.ForeignKey(
        Severity, on_delete=models.CASCADE, blank=True, null=True
    )

    executions = models.ManyToManyField("testruns.TestExecution", related_name="bugs")
    tags = models.ManyToManyField("management.Tag", related_name="bugs")

    def __str__(self):
        return f"BUG-{self.pk}: {self.summary} "

    def save(self, *args, **kwargs):
        # Sync boolean status with status_code
        if self.status_code in [BugStatus.CLOSED, BugStatus.RESOLVED, BugStatus.WONT_FIX]:
            self.status = False
        else:
            self.status = True
        super().save(*args, **kwargs)

    @property
    def status_label(self):
        return dict(BugStatus.choices).get(self.status_code, self.status_code)

    @property
    def status_badge_class(self):
        mapping = {
            BugStatus.STUCK: "label-danger",
            BugStatus.IN_PROGRESS: "label-warning",
            BugStatus.OPEN: "label-primary",
            BugStatus.RESOLVED: "label-success",
            BugStatus.CLOSED: "label-default",
            BugStatus.WONT_FIX: "label-default",
        }
        return mapping.get(self.status_code, "label-primary")

    @property
    def status_badge_icon(self):
        mapping = {
            BugStatus.STUCK: "fa fa-exclamation-triangle",
            BugStatus.IN_PROGRESS: "fa fa-clock-o",
            BugStatus.OPEN: "fa fa-envelope-open",
            BugStatus.RESOLVED: "fa fa-check-circle",
            BugStatus.CLOSED: "fa fa-times-circle",
            BugStatus.WONT_FIX: "fa fa-ban",
        }
        return mapping.get(self.status_code, "fa fa-info-circle")

    def _get_absolute_url(self):
        return reverse(
            "bugs-get",
            args=[
                self.pk,
            ],
        )

    def get_absolute_url(self):
        return self._get_absolute_url()
