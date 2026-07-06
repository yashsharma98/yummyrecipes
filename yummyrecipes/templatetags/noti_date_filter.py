from datetime import datetime

from django import template

register = template.Library()


@register.filter
def total_days_ago(value):
    now = datetime.now(value.tzinfo)
    delta = now - value
    total_days = delta.days
    return f"{total_days} days ago"
