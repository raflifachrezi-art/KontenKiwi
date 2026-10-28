# -*- coding: utf-8 -*-

import datetime
import secrets

from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
        verbose_name=_("User"),
    )
    monday_api_token = models.CharField(
        max_length=512,
        blank=True,
        null=True,
        verbose_name=_("Monday.com API Token"),
        help_text=_(
            "Personal API Token dari akun Monday.com Anda (Avatar > Developers > My Access Tokens)."
        ),
    )
    monday_user_id = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        verbose_name=_("Monday.com User ID"),
        help_text=_("User ID Monday.com Anda (misal: 115783524)."),
    )

    class Meta:
        verbose_name = _("User Profile")
        verbose_name_plural = _("User Profiles")

    def __str__(self):
        return f"Profile of {self.user.username}"


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_or_save_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
    else:
        UserProfile.objects.get_or_create(user=instance)


def get_user_profile(user):
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile


class UserActivationKey(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    activation_key = models.CharField(max_length=64, null=True, blank=True)
    key_expires = models.DateTimeField(null=True, blank=True)

    @classmethod
    def set_random_key_for_user(cls, user, force=False):
        activation_key = secrets.token_hex()

        # Create and save their profile
        user_activation_key, created = cls.objects.get_or_create(user=user)
        if created or force:
            user_activation_key.activation_key = activation_key
            user_activation_key.key_expires = (
                datetime.datetime.today() + datetime.timedelta(7)
            )
            user_activation_key.save()

        return user_activation_key
