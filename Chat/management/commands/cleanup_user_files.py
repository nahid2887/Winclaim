from django.core.management.base import BaseCommand
from Chat.models import ChatSession
import os
import shutil
from datetime import datetime, timedelta
from django.utils import timezone

class Command(BaseCommand):
    help = 'Clean up old user upload folders for inactive sessions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Delete folders for sessions inactive for this many days (default: 7)'
        )

    def handle(self, *args, **options):
        days = options['days']
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Find inactive sessions older than cutoff date
        old_sessions = ChatSession.objects.filter(
            is_active=False,
            updated_at__lt=cutoff_date
        )
        
        cleaned_count = 0
        for session in old_sessions:
            try:
                user_folder_name = f"user_{session.user.user_id}_{str(session.session_id)[:8]}"
                user_upload_path = os.path.join('media', 'chat_uploads', user_folder_name)
                
                if os.path.exists(user_upload_path):
                    shutil.rmtree(user_upload_path)
                    cleaned_count += 1
                    self.stdout.write(f"Cleaned up folder: {user_folder_name}")
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Error cleaning session {session.session_id}: {e}")
                )
        
        self.stdout.write(
            self.style.SUCCESS(f"Successfully cleaned up {cleaned_count} user folders")
        )
