from django import template

register = template.Library()

@register.filter
def get_visit_count(visited_blogs, blog_pk):
    return visited_blogs.get(blog_pk, 0)
