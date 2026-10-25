from datetime import timedelta
import time,logging
from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from market.models import Outbox,Order,Refund,RateBucket
from market import payments
log=logging.getLogger(__name__)
class Command(BaseCommand):
    help='Process transactional email, pending refunds, transfer recoveries and expired reservations. No automatic seller payouts.'
    def add_arguments(self,parser): parser.add_argument('--loop',action='store_true')
    def handle(self,*args,**options):
        while True:
            self.cycle()
            if not options['loop']: break
            time.sleep(30)
    def cycle(self):
        now=timezone.now()
        ids=list(Outbox.objects.filter(sent_at=None,attempts__lt=10).filter(Q(retry_at=None)|Q(retry_at__lte=now)).values_list('pk',flat=True)[:50])
        for pk in ids:
            with transaction.atomic():
                item=Outbox.objects.select_for_update().get(pk=pk)
                if item.sent_at or (item.retry_at and item.retry_at>timezone.now()): continue
                item.attempts+=1
                try:
                    count=send_mail(item.subject,item.body,settings.DEFAULT_FROM_EMAIL,[item.recipient],fail_silently=False)
                    if count!=1: raise RuntimeError('Mail not accepted by configured backend')
                    item.sent_at=timezone.now()
                except Exception:
                    item.retry_at=timezone.now()+timedelta(seconds=min(3600,30*2**item.attempts))
                    log.warning('Mail retry scheduled for outbox id %s',item.pk)
                item.save(update_fields=['attempts','sent_at','retry_at'])
        if settings.PAYMENTS_MODE!='disabled':
            for r in Refund.objects.filter(status__in=['requested','pending'])[:20]:
                try: payments.execute_refund(r.pk)
                except Exception: log.warning('Refund needs retry: %s',r.pk)
            for r in Refund.objects.filter(status='succeeded',recovery_id='',part__transferred_cents__gt=0).order_by('created_at')[:20]:
                try: payments.recover_refund(r.pk)
                except Exception: log.warning('Transfer recovery unresolved: %s',r.pk)
        for o in Order.objects.filter(status='pending',expires_at__lt=now)[:50]:
            try: payments.cancel_pending(o,expire=True)
            except Exception: log.warning('Order remains reserved pending processor confirmation: %s',o.pk)
        RateBucket.objects.filter(expires_at__lt=now).delete()
