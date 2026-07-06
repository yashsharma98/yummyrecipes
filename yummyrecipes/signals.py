from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import UserProfile, profile

User = get_user_model()


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        profile.objects.create(user=instance)


# for creating a default theme when new user register's
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def assign_initial_credits(sender, instance, created, **kwargs):
    if created:
        instance.credits = 5
        instance.save()


@receiver(post_save, sender=User)
def save_Profile(sender, instance, **kwargs):
    instance.profile.save()

    # for default theme when new user register's
    # instance.userprofile.save()
