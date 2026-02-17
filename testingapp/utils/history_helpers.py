from testingapp.models import BlogHistory


def get_historys_pk(user):
    if not user.is_authenticated:
        return []
    return list(BlogHistory.objects.filter(user=user).values_list("blog_post__pk", flat=True).distinct())
