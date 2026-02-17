from datetime import date

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.forms import ModelForm
from tinymce.widgets import TinyMCE

from .models import Feedback, YearlyGoal, comments, photo, post, profile


class registration_form(UserCreationForm):
    fname = forms.CharField(max_length=200)
    lname = forms.CharField(max_length=200)
    email = forms.EmailField(max_length=200)
    password1 = forms.CharField(max_length=200)
    password2 = forms.CharField(max_length=200)

    class Meta:
        model = User
        fields = ["fname", "lname", "email", "password1", "password2"]

    def user_exit(self):
        username = self.cleaned_data["email"]
        if User.objects.filter(username=username).exists():
            return True

        return False

    def save(self):
        fname = self.cleaned_data["fname"]
        lname = self.cleaned_data["lname"]
        email = username = self.cleaned_data["email"]
        password = self.cleaned_data["password1"]

        User.objects.create_user(username=username, first_name=fname, last_name=lname, email=email, password=password)


class UpdateProfile(forms.ModelForm):
    help_text = (
        "Raw passwords are not stored, so there is no way to see "
        "this user's password, but you can change the password "
        'using <a href="password/">this form</a>.'
    )

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email")
        help_texts = {
            "password ": (""),
        }


class post_form(ModelForm):
    title = forms.CharField()
    ingredients = forms.CharField()
    content = forms.CharField(widget=TinyMCE(attrs={"cols": 100, "rows": 30}))
    # content = RichTextField()
    # content = forms.CharField(max_length=10000)
    # timing = forms.IntegerField()
    servings = forms.IntegerField()
    type = forms.CharField(max_length=100)
    cuisine = forms.CharField(max_length=100)
    category = forms.CharField(max_length=100)
    difficulty = forms.CharField(max_length=100)

    class Meta:
        model = post
        fields = ["title", "content", "ingredients", "servings", "type", "cuisine", "category", "difficulty"]
        # fields = ['title','content','ingredients','image','timing','servings','type','cuisine','category']

    def title_exists(self):
        title = self.cleaned_data["title"]
        if post.objects.filter(title=title).exists():
            return True
        return False

    # def title_exists(self):
    #     title = self.cleaned_data['title']
    #     if post.objects.filter(title=title).exists():
    #         return True
    #     return False

    # def both_exists(self):
    #     ingredients = self.cleaned_data['ingredients']
    #     title = self.cleaned_data['title']
    #     if post.objects.filter(ingredients=ingredients,title=title).exists():
    #         return True
    #     return False

    # return False
    # ingredients = self.cleaned_data.get('ingredients')
    # for instance in post.objects.all():
    #     if instance.ingredients == ingredients:
    #         pass
    # return ingredients


class FileModelForm(ModelForm):
    image = forms.ImageField(required=False)

    class Meta:
        model = photo
        fields = ["image"]


class ImageGenerationForm(forms.Form):
    title = forms.CharField(max_length=255)


class AIRecipeGenerationForm(forms.Form):
    title = forms.CharField(max_length=255)


class AIcolorCodeGenerationForm(forms.Form):
    title = forms.CharField(max_length=255)


class comment_form(ModelForm):
    comment = forms.Textarea()

    class Meta:
        model = comments
        fields = ["comment"]

    # def save(self,request):
    #     title = self.cleaned_data['title']
    #     content = self.cleaned_data['content']

    #     post.objects.create(title=title,content=content,author=request.user)


class Updatepro(forms.ModelForm):
    first_name = forms.CharField(max_length=100)
    last_name = forms.CharField(max_length=100)
    email = forms.CharField(max_length=50)
    help_text = (
        "Raw passwords are not stored, so there is no way to see "
        "this user's password, but you can change the password "
        'using <a href="password/">this form</a>.'
    )

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email")
        help_texts = {
            "password ": (""),
        }


class Updateview(forms.ModelForm):
    profile_img = forms.ImageField()
    dob = forms.CharField(max_length=20)
    gender = forms.CharField(max_length=10)
    bio = forms.CharField(max_length=114)
    facebook = forms.URLField(max_length=400, required=False)
    instagram = forms.URLField(max_length=400, required=False)
    twitter = forms.URLField(max_length=400, required=False)
    threads = forms.URLField(max_length=400, required=False)
    youtube = forms.URLField(max_length=400, required=False)
    website = forms.URLField(max_length=400, required=False)

    class Meta:
        model = profile
        fields = ("profile_img", "dob", "gender", "bio", "facebook", "instagram", "twitter", "threads", "youtube", "website")


class LocationForm(forms.Form):
    location = forms.CharField(max_length=100, label="Location")


class SearchForm(forms.Form):
    query = forms.CharField(label="Search", required=False)


class EmailNotificationForm(forms.Form):
    send_email = forms.BooleanField(required=False, label="Receive Email Notifications")


class UseColorFromImageForm(forms.Form):
    use_colors_from_image = forms.BooleanField(required=False, label="Use colors from image")


class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        exclude = ["user"]


class PreferencesForm(forms.ModelForm):
    class Meta:
        model = profile
        fields = ["preference_type", "preference_category", "preference_cuisine"]


class YearlyGoalForm(forms.ModelForm):
    class Meta:
        model = YearlyGoal
        fields = ["goal"]

    def clean(self):
        cleaned_data = super().clean()
        year = self.instance.year  # Year from the instance
        if year != date.today().year:
            raise forms.ValidationError("You can only modify goals for the current year.")
        return cleaned_data
