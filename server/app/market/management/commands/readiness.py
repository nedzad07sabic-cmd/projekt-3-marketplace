from django.conf import settings
from django.core.management.base import BaseCommand,CommandError
from django.db import connection
from django_otp.plugins.otp_totp.models import TOTPDevice
from market.services import legal_ready
from market.models import Outbox
class Command(BaseCommand):
    help='Fail-closed launch checks; not a certification of legal compliance or external payment acceptance.'
    def handle(self,*a,**kw):
        checks={
            'DEBUG disabled':not settings.DEBUG,
            'PostgreSQL':connection.vendor=='postgresql',
            'HTTPS origin':settings.SITE_URL.startswith('https://'),
            'Explicit hosts':bool(settings.ALLOWED_HOSTS) and '*' not in settings.ALLOWED_HOSTS,
            'Private application key':len(settings.SECRET_KEY)>=50 and 'local-development' not in settings.SECRET_KEY,
            'Real SMTP configuration':settings.EMAIL_BACKEND.endswith('smtp.EmailBackend') and bool(settings.EMAIL_HOST) and '@localhost' not in settings.DEFAULT_FROM_EMAIL,
            'Administrator OTP enrolled':TOTPDevice.objects.filter(user__is_staff=True,confirmed=True).exists(),
            'Approved legal pages':legal_ready(),
            'Support address configured':bool(settings.SUPPORT_EMAIL),
            'Payment provider written approval recorded':settings.PROVIDER_APPROVED,
            'Private-seller written approval recorded':settings.PRIVATE_SELLERS_APPROVED,
            'Live release explicitly approved':settings.LIVE_APPROVED,
            'Live API key configured':settings.PAYMENTS_MODE=='live' and settings.STRIPE_SECRET_KEY.startswith('sk_live_'),
            'Both signed webhook secrets configured':bool(settings.STRIPE_WEBHOOK_SECRET and settings.STRIPE_CONNECT_WEBHOOK_SECRET),
            'No exhausted transactional email retries':not Outbox.objects.filter(sent_at=None,attempts__gte=10).exists(),
        }
        for k,v in checks.items(): self.stdout.write(('PASS ' if v else 'BLOCK ')+k)
        if not all(checks.values()): raise CommandError('Not ready for live commerce. Fix blockers and run end-to-end external acceptance tests; never bypass by simply renaming test mode.')
        self.stdout.write('Configuration checks passed. External acceptance, legal/financial review, backups and operational staffing are still required.')
