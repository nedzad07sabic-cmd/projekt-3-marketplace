from django import template
from ..services import money
register=template.Library()
register.filter('money',money)
@register.filter
def shortid(value): return str(value)[:8].upper()
