from django import template

register = template.Library()


@register.filter
def pluralize_min(minutes):
    return f"{minutes} min{'s' if minutes > 1 else ''} read"
