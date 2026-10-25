from django.conf import settings
from django.db.models import Sum
from .models import Category,LegalPage

def site_context(request):
    count=0
    if request.user.is_authenticated: count=request.user.cart_lines.aggregate(n=Sum('quantity'))['n'] or 0
    return {'site_name':settings.SITE_NAME,'categories':Category.objects.filter(enabled=True),'cart_count':count,'payment_mode':settings.PAYMENTS_MODE,'registration_open':settings.REGISTRATION_OPEN,'legal_links':LegalPage.objects.filter(approved=True).order_by('slug')}
