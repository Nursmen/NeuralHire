from django import template
import re

# Register the template library
register = template.Library()

@register.filter
def split_by_comma(value):
    """
    Splits a string by a comma (,) and returns a list.
    Handles the case where the input value is not a string.
    """
    if isinstance(value, str):
        value = value.replace('[', '').replace(']', '').replace("'", "").replace('"', '')
        return value.split(',')
    return []

@register.filter
def get_link(value):
    """
    Splits a string by a comma (,) and returns a list.
    Handles the case where the input value is not a string.
    """
    if isinstance(value, str):
        value = re.sub(r'/vacancy/search/\?page=\d+/', '/', value)
        return value.strip()
    return value