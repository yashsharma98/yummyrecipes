from django.contrib import admin

from .models import (
    BlogHistory,
    CreditHistory,
    CreditSpentHistory,
    Favorite,
    Feedback,
    Follow,
    RecipeRecommendationHistory,
    RedeemedCredit,
    UserLocation,
    UserProfile,
    UserTasteProfile,
    YearlyGoal,
    comments,
    photo,
    post,
    profile,
    searchedRecipesRanking,
)

# Register your models here.


class photoInline(admin.TabularInline):
    model = photo


class postAdmin(admin.ModelAdmin):
    inlines = [
        photoInline,
    ]


admin.site.register(post, postAdmin)

admin.site.register(profile)

admin.site.register(comments)

admin.site.register(photo)

admin.site.register(BlogHistory)

admin.site.register(UserProfile)

admin.site.register(UserLocation)

admin.site.register(Favorite)

admin.site.register(RedeemedCredit)

admin.site.register(CreditHistory)

admin.site.register(CreditSpentHistory)

admin.site.register(Feedback)

admin.site.register(Follow)

admin.site.register(searchedRecipesRanking)

admin.site.register(YearlyGoal)

admin.site.register(UserTasteProfile)

admin.site.register(RecipeRecommendationHistory)
