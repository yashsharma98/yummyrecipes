from allauth.account.signals import user_signed_up
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver

from testingapp.tasks.trending_post_tasks import update_trending_posts

from .models import UserProfile, post, profile
from .utils.email_utils import send_welcome_email

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


@receiver(user_signed_up)
def send_welcome_email_signal(request, user, **kwargs):
    if user.email:
        send_welcome_email(request, user.email, user.first_name)


@receiver(post_save, sender=post)
def generate_embedding(sender, instance, created, **kwargs):
    if created and not instance.embedding:
        text = (
            f"{instance.title} "
            f"{instance.category or ''} "
            f"{instance.cuisine or ''} "
            f"{instance.type or ''} "
            f"{instance.timing or ''} minutes "
            f"{instance.difficulty or ''}"
        )

        from testingapp.search.text_embeddings import recipe_embedding

        try:
            vector_list = recipe_embedding(text)
            instance.embedding = vector_list

            # Save the embedding to database
            instance.save(update_fields=["embedding"])

        except Exception as e:
            print(f"Failed to generate embedding for recipe {instance.id}: {e}")


# trigger update on like and views (hitcounts) handled by celery in settings
@receiver(m2m_changed, sender=post.likes.through)
@receiver(post_save, sender=post)
def update_trending_cache(sender, **kwargs):
    update_trending_posts.delay()
