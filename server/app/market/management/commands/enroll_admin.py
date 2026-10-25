from django.core.management.base import BaseCommand,CommandError
from django_otp.plugins.otp_totp.models import TOTPDevice
from market.models import User
class Command(BaseCommand):
    help='Create an OTP device for an existing administrator. Run only on a private terminal, not in CI logs.'
    def add_arguments(self,parser): parser.add_argument('username')
    def handle(self,username,**options):
        try: user=User.objects.get(username=username,is_staff=True)
        except User.DoesNotExist: raise CommandError('Administrator not found. Run createsuperuser first.')
        if TOTPDevice.objects.filter(user=user,confirmed=True).exists(): raise CommandError('An OTP device already exists. Do not replace it without a controlled recovery process.')
        device=TOTPDevice.objects.create(user=user,name='Administrator authenticator',confirmed=True)
        self.stdout.write('PRIVATE OTP ENROLLMENT URI — store in your authenticator, do not share or commit:')
        self.stdout.write(device.config_url)
