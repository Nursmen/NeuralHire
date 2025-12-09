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
    Cleans up vacancy links by removing page parameters.
    """
    if isinstance(value, str):
        value = re.sub(r'/vacancy/search/\?page=\d+/', '/', value)
        return value.strip()
    return value


@register.filter
def index(lst, i):
    """
    Returns the item at index i from list lst.
    Used to access list items in templates.
    """
    try:
        return lst[int(i)]
    except (IndexError, ValueError, TypeError):
        return None


@register.filter
def clean_company(value):
    """
    Removes rating numbers (like 6.3) from company names.
    """
    if isinstance(value, str):
        # Remove patterns like "6.3" or "4.5" at the end
        value = re.sub(r'\d+\.\d+\s*$', '', value)
        return value.strip()
    return value
