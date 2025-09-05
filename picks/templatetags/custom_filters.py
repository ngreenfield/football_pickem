from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    print(f"get_item called with key={key}")
    return dictionary.get(key)

@register.filter
def to_range(value):
    """Return range from 1 to value (inclusive)."""
    try:
        value = int(value)
        return range(1, value + 1)
    except (ValueError, TypeError):
        return []