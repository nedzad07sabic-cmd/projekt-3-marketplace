from datetime import timedelta
import hashlib,hmac,time
from django.conf import settings
from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from .models import RateBucket

class RateLimitMiddleware:
    """Shared DB-backed limit. No plain IP addresses are stored.
    TRUST_PROXY must only be enabled behind the bundled, non-bypassable proxy.
    """
    def __init__(self,get_response): self.get_response=get_response
    def __call__(self,request):
        if settings.RATE_LIMIT_ENABLED and request.method=='POST' and not request.path.startswith('/payments/webhook/'):
            ip=request.META.get('HTTP_X_REAL_IP','') if settings.TRUST_PROXY else request.META.get('REMOTE_ADDR','')
            bucket=int(time.time())//600
            is_auth=request.path.startswith('/account/') or request.path.startswith('/manage/login')
            limit=20 if is_auth else 100
            groups=[f'ip:{ip}:{"auth" if is_auth else "write"}:{bucket}']
            if is_auth:
                identity=str(request.POST.get('username') or request.POST.get('email') or '').lower()[:254]
                if identity: groups.append(f'identity:{identity}:{bucket}')
            for value in groups:
                key=hmac.new(settings.SECRET_KEY.encode(),value.encode(),hashlib.sha256).hexdigest()
                with transaction.atomic():
                    obj,_=RateBucket.objects.get_or_create(key=key,defaults={'expires_at':timezone.now()+timedelta(minutes=20)})
                    obj=RateBucket.objects.select_for_update().get(pk=obj.pk)
                    obj.count+=1;obj.save(update_fields=['count'])
                    if obj.count>limit:
                        response=HttpResponse('Previše pokušaja. Pokušaj ponovo kasnije.',status=429)
                        response['Retry-After']='600';return response
        return self.get_response(request)

class HeadersMiddleware:
    def __init__(self,get_response): self.get_response=get_response
    def __call__(self,request):
        response=self.get_response(request)
        if not request.path.startswith('/manage/'):
            response['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; form-action 'self' https://checkout.stripe.com https://connect.stripe.com; base-uri 'none'; object-src 'none'; frame-ancestors 'none'"
        response['Referrer-Policy']='strict-origin-when-cross-origin'
        response['Permissions-Policy']='camera=(), microphone=(), geolocation=()'
        if request.user.is_authenticated or request.path.startswith(('/account/','/orders/','/sell/','/ops/','/cases/')):
            response['Cache-Control']='private, no-store'
        if settings.PAYMENTS_MODE!='live': response['X-Robots-Tag']='noindex, nofollow'
        return response
