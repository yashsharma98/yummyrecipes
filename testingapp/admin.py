from django.contrib import admin
from .models import post
from .models import profile
from .models import comments
from .models import photo
from .models import BlogHistory
from .models import UserProfile
from .models import UserLocation
from .models import Favorite
from .models import RedeemedCredit
from .models import CreditHistory
from .models import CreditSpentHistory


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
