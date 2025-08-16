from django.core.management.base import BaseCommand
from Chat.models import UserClaimUpload


class Command(BaseCommand):
    help = 'Test UserClaimUpload model functionality'

    def handle(self, *args, **options):
        self.stdout.write('UserClaimUpload model is ready!')
        
        # Show count of existing uploads
        count = UserClaimUpload.objects.count()
        self.stdout.write(f'Current UserClaimUpload records: {count}')
