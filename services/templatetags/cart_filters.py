from django import template

register = template.Library()

@register.filter
def sum_attr(items, attr):
    """Sum the values of a specific attribute from a list of items"""
    return sum(getattr(item, attr) for item in items)

@register.filter
def test_filter(value):
    """A simple test filter to verify template tags are working"""
    return f"Test: {value}" 