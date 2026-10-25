import csv,sys
from django.core.management.base import BaseCommand
from market.models import SellerOrder
class Command(BaseCommand):
    help='Export operational seller-order ledger to a protected destination. This is NOT a DAC7 filing or tax return.'
    def handle(self,*a,**kw):
        writer=csv.writer(sys.stdout)
        writer.writerow(['seller_order_id','seller_id','order_id','created_at','currency','gross_cents','commission_cents','refund_cents','commission_refund_cents','transferred_cents','recovered_cents','recovery_due_cents'])
        for p in SellerOrder.objects.select_related('order').order_by('order__created_at').iterator():
            writer.writerow([str(p.pk),str(p.seller_id),str(p.order_id),p.order.created_at.isoformat(),p.order.currency,p.total_cents,p.commission_cents,p.refunded_cents,p.commission_refunded_cents,p.transferred_cents,p.recovered_cents,p.recovery_due_cents])
