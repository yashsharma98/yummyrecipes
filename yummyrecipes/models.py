import math
import os
from datetime import date, datetime

from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericRelation
from django.core.files.storage import default_storage
from django.core.validators import MinValueValidator, URLValidator

# from hashlib import new
from django.db import models
from django.db.models import Count, F, Sum
from django.urls import reverse
from django.utils import timezone
from hitcount.models import HitCount, HitCountMixin
from pgvector.django import VectorField
from storages.backends import s3boto3
from tinymce.models import HTMLField

# Create your models here.


class profile(models.Model):
    GENDER_CHOICES = (
        ("Male", "Male"),
        ("Female", "Female"),
    )

    recipes_preference_type = (
        ("Select", "Select"),
        ("Breakfast recipes", "Breakfast recipes"),
        ("Lunch recipes", "Lunch recipes"),
        ("Evening Snack recipes", "Evening Snack recipes"),
        ("Dinner recipes", "Dinner recipes"),
    )

    recipes_preference_category = (
        ("Select", "Select"),
        ("Veg recipes", "Veg recipes"),
        ("Non-Veg recipes", "Non-Veg recipes"),
    )

    recipes_preference_cuisine = (
        ("Select", "Select"),
        ("Indian cuisine", "Indian cuisine"),
        ("American cuisine", "American cuisine"),
        ("Italian cuisine", "Italian cuisine"),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    profile_img = models.ImageField(default="avatar.jpg", upload_to="profile")
    dob = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES, null=True, blank=True)
    bio = models.TextField(default="Bio")
    hit_count = models.OneToOneField(HitCount, null=True, blank=True, on_delete=models.CASCADE)
    send_email = models.BooleanField(default=True)
    credits = models.IntegerField(default=10, validators=[MinValueValidator(0)])
    earned_credits = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    redeemed_credits = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    credits_spent = models.PositiveIntegerField(default=0)

    facebook = models.URLField(max_length=400, blank=True, validators=[URLValidator()])
    instagram = models.URLField(max_length=400, blank=True, validators=[URLValidator()])
    twitter = models.URLField(max_length=400, blank=True, validators=[URLValidator()])
    threads = models.URLField(max_length=400, blank=True, validators=[URLValidator()])
    youtube = models.URLField(max_length=400, blank=True, validators=[URLValidator()])
    website = models.URLField(max_length=400, blank=True, validators=[URLValidator()])

    preference_type = models.CharField(max_length=100, choices=recipes_preference_type, default="Select")
    preference_category = models.CharField(max_length=100, choices=recipes_preference_category, default="Select")
    preference_cuisine = models.CharField(max_length=100, choices=recipes_preference_cuisine, default="Select")

    # credits = models.DecimalField(default=5, max_digits=10, decimal_places=2)

    def __str__(self):
        return self.user.username + " Profile"

    # def get_absolute_url(self):
    #     return reverse('profile')

    def save(self, *args, **kwargs):
        super(profile, self).save(*args, **kwargs)


class YearlyGoal(models.Model):
    profile = models.ForeignKey(profile, on_delete=models.CASCADE, related_name="yearly_goals")
    year = models.IntegerField(default=date.today().year)
    goal = models.IntegerField(default=0)

    class Meta:
        unique_together = ("profile", "year")

    def __str__(self):
        return f"{self.year}: {self.goal} recipes"


class post(models.Model, HitCountMixin):
    title = models.CharField(max_length=1500)
    ingredients = HTMLField(blank=True, null=True)
    content = HTMLField(blank=True, null=True)
    # content = RichTextField(blank=True, null=True)
    # content = models.TextField()
    date_post = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    views = models.IntegerField(default=0)
    timing = models.IntegerField(default=0, blank=True)
    servings = models.IntegerField(default=0)
    type = models.CharField(max_length=100, default="type")
    cuisine = models.CharField(max_length=100, default="cuisine")
    category = models.CharField(max_length=100, default="category")
    # city = models.CharField(max_length=100, default="city")
    likes = models.ManyToManyField(profile, related_name="likes")
    dislikes = models.ManyToManyField(profile, related_name="dislikes")
    favourites = models.ManyToManyField(User, related_name="favourite", default=None, blank=True)
    date_modified = models.DateTimeField(auto_now=True)
    difficulty = models.CharField(max_length=100, default="difficulty")
    hit_count_generic = GenericRelation(HitCount, object_id_field="object_pk", related_query_name="hit_count_generic_relation")
    embedding = VectorField(null=True, blank=True)

    def __str__(self):
        return self.title + " - " + self.author.username
        # return self.title + " - "+self.author.username

    def get_date(self):
        return self.date_post.date()

    def get_modified_date(self):
        return self.date_modified.date()

    def get_absolute_url(self):
        return reverse("home")

    def read_time(self):
        words_per_minute = 200
        total_words = len(self.content.split())
        minutes = total_words / words_per_minute
        return round(minutes)

    def total_likes(self):
        return self.likes.all().count()

    def total_dislikes(self):
        return self.dislikes.all().count()

    def whenpublished(self):
        now = timezone.now()

        diff = now - self.date_post

        if diff.days == 0 and diff.seconds >= 0 and diff.seconds < 60:
            seconds = diff.seconds

            if seconds == 1:
                return str(seconds) + "second ago"

            else:
                return str(seconds) + " seconds ago"

        if diff.days == 0 and diff.seconds >= 60 and diff.seconds < 3600:
            minutes = math.floor(diff.seconds / 60)

            if minutes == 1:
                return str(minutes) + " minute ago"

            else:
                return str(minutes) + " minutes ago"

        if diff.days == 0 and diff.seconds >= 3600 and diff.seconds < 86400:
            hours = math.floor(diff.seconds / 3600)

            if hours == 1:
                return str(hours) + " hour ago"

            else:
                return str(hours) + " hours ago"

        # 1 day to 30 days
        if diff.days >= 1 and diff.days < 30:
            days = diff.days

            if days == 1:
                return str(days) + " day ago"

            else:
                return str(days) + " days ago"

        if diff.days >= 30 and diff.days < 365:
            months = math.floor(diff.days / 30)

            if months == 1:
                return str(months) + " month ago"

            else:
                return str(months) + " months ago"

        if diff.days >= 365:
            years = math.floor(diff.days / 365)

            if years == 1:
                return str(years) + " year ago"

            else:
                return str(years) + " years ago"

    def get_recipe_url(self):
        return reverse("viewpost", kwargs={"pk": self.pk})

    @classmethod
    def top_performing_recipes(cls, user):
        posts = cls.objects.filter(author=user).annotate(
            total_likes=Count("likes"), total_views=Sum("hit_count_generic__hits"), total_comments=Count("comments")
        )

        posts = posts.annotate(performance_score=(2 * F("total_likes") + F("total_views") + F("total_comments"))).order_by("-performance_score")[:2]
        # more importance given to likes

        return posts

    @property
    def image_url(self):
        photo_obj = self.photo_set.first()
        if photo_obj and photo_obj.image:
            return photo_obj.image.url
        return None

    @property
    def author_profile_img(self):
        if self.author and hasattr(self.author, "profile") and self.author.profile.profile_img:
            return self.author.profile.profile_img.url
        return None


class photo(models.Model):
    image = models.ImageField(upload_to="images/")
    feed = models.ForeignKey(post, on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        # If the image field is not empty
        if self.image:
            # Switch storage backend based on environment
            if "DATABASE_URL" in os.environ:
                # Running on Render (production environment)
                self.image.storage = s3boto3.S3Boto3Storage()
            else:
                # Running locally
                self.image.storage = default_storage
        super().save(*args, **kwargs)

    def __str__(self):
        return self.feed.title + " - " + self.feed.author.username


class UserLocation(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    location = models.CharField(max_length=200, default="Location", null=True, blank=True)

    def __str__(self):
        return self.location


class comments(models.Model):
    date_comment = models.DateTimeField(default=timezone.now)
    date_update_comment = models.DateTimeField(default=timezone.now)
    post_super = models.ForeignKey(post, on_delete=models.CASCADE)
    comment_user = models.ForeignKey(User, on_delete=models.CASCADE)
    comment = models.TextField()

    def __str__(self):
        return self.post_super.title + " - " + self.comment_user.first_name

    def get_date(self):
        return self.date_comment.date()


class BlogHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="blog_histories")
    blog_post = models.ForeignKey(post, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.blog_post.title + " -" + " BlogHistory"

    def time_stamp(self):
        return self.timestamp.date()


class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    blog = models.ForeignKey(post, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.blog.title + " -" + " Favorite"


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    primary_color = models.CharField(max_length=20, null=True, blank=True, default="#DBCBBD")
    secondary_color = models.CharField(max_length=20, null=True, blank=True, default="#F0ECE3")
    tertiary_color = models.CharField(max_length=20, null=True, blank=True, default="#221e20")
    active_link_color = models.CharField(max_length=20, null=True, blank=True, default="#9F8772")
    hover_color = models.CharField(max_length=20, null=True, blank=True, default="#9C938B")

    # theme = models.CharField(max_length=100, null=True, blank=True, default="theme")
    theme = models.CharField(max_length=20, default="day")
    neutral_primary = models.CharField(max_length=20, null=True, blank=True, default="#DBCBBD")
    neutral_secondary = models.CharField(max_length=20, null=True, blank=True, default="#D8D9DA")

    schedule_enabled = models.BooleanField(default=False)
    schedule_mode = models.CharField(max_length=10, default="auto")
    night_start = models.TimeField(null=True, blank=True)
    night_end = models.TimeField(null=True, blank=True)
    theme_name = models.CharField(max_length=100, blank=True, default="")

    use_colors_from_image = models.BooleanField(default=False)

    def __str__(self):
        return self.user.username


class RedeemedCredit(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.IntegerField(validators=[MinValueValidator(0)])
    redeemed_timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.amount} - {self.redeemed_timestamp.date()}"


class CreditHistory(models.Model):
    CREDIT_ACTIONS = (
        ("earned", "Earned"),
        ("redeemed", "Redeemed"),
        ("new_recipe", "New recipe"),
        ("deleted", "Deleted"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.IntegerField(validators=[MinValueValidator(0)])
    earned_timestamp = models.DateTimeField(auto_now_add=True)
    credit_action = models.CharField(max_length=20, null=True, choices=CREDIT_ACTIONS)

    def __str__(self):
        return f"{self.user.username} - {self.amount} - {self.earned_timestamp.date()}"


class CreditSpentHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    recipename = models.ForeignKey(post, on_delete=models.CASCADE)
    amount = models.IntegerField()
    spent_timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.spent_timestamp.date()}"


class Feedback(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=250)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name}"


class Follow(models.Model):
    follower = models.ForeignKey(User, related_name="following", on_delete=models.CASCADE)
    following = models.ForeignKey(User, related_name="followers", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("follower", "following")

    def __str__(self):
        return f"{self.follower.username} follows {self.following.username}"

    def follow_since(self):
        now = timezone.now()

        diff = now - self.created_at

        if diff.days == 0 and diff.seconds >= 0 and diff.seconds < 60:
            seconds = diff.seconds

            if seconds == 1:
                return str(seconds) + "second ago"

            else:
                return str(seconds) + " seconds ago"

        if diff.days == 0 and diff.seconds >= 60 and diff.seconds < 3600:
            minutes = math.floor(diff.seconds / 60)

            if minutes == 1:
                return str(minutes) + " minute ago"

            else:
                return str(minutes) + " minutes ago"

        if diff.days == 0 and diff.seconds >= 3600 and diff.seconds < 86400:
            hours = math.floor(diff.seconds / 3600)

            if hours == 1:
                return str(hours) + " hour ago"

            else:
                return str(hours) + " hours ago"

        # 1 day to 30 days
        if diff.days >= 1 and diff.days < 30:
            days = diff.days

            if days == 1:
                return str(days) + " day ago"

            else:
                return str(days) + " days ago"

        if diff.days >= 30 and diff.days < 365:
            months = math.floor(diff.days / 30)

            if months == 1:
                return str(months) + " month ago"

            else:
                return str(months) + " months ago"

        if diff.days >= 365:
            years = math.floor(diff.days / 365)

            if years == 1:
                return str(years) + " year ago"

            else:
                return str(years) + " years ago"


class searchedRecipesRanking(models.Model):
    recipe = models.ForeignKey(post, on_delete=models.CASCADE, related_name="recipe_rankings")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_search_rankings")
    date_searched = models.DateTimeField(default=datetime.now)

    class Meta:
        unique_together = ("recipe", "user")


class UserTasteProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    taste_vector = VectorField()
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} taste profile"


class RecipeRecommendationHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    recipe = models.ForeignKey(post, on_delete=models.CASCADE)
    score = models.FloatField()
    shown_at = models.DateTimeField(auto_now_add=True)
    clicked = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} → {self.recipe.title}"
