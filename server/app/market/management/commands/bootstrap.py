from django.core.management.base import BaseCommand
from market.models import Category
class Command(BaseCommand):
    help='Create category definitions only. Never creates customers, products, admin passwords or fake reviews.'
    def handle(self,*args,**options):
        for slug,name,symbol,rate in [('electronics','Elektronika i gaming','⌘',900),('home','Dom i bašta','⌂',1000),('fashion','Moda','◇',1000),('sport','Sport i hobi','◉',1000),('books','Knjige i mediji','▤',1000),('other','Ostalo','✦',1000)]:
            Category.objects.get_or_create(slug=slug,defaults={'name':name,'symbol':symbol,'commission_bps':rate})
        self.stdout.write('Categories created. Rates are configuration defaults, not an approved price list. No products or users inserted.')
