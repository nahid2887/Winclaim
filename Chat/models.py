from django.db import models
from accounts.models import CustomUser
import uuid
import os
import shutil
import json
from django.utils import timezone
from django.conf import settings

class ChatSession(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='chat_sessions')
    session_id = models.UUIDField(unique=True, editable=False, default=uuid.uuid4)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)  # Track last activity
    is_active = models.BooleanField(default=True)  # Track if session is still active

    class Meta:
        ordering = ['-updated_at']  # Most recently used first

    def __str__(self):
        return f"Chat Session {self.session_id} - {self.user.email}"

    def cleanup_user_files(self):
        """Clean up user's uploaded files when session is deactivated"""
        try:
            user_folder_name = f"user_{self.user.user_id}_{str(self.session_id)[:8]}"
            user_upload_path = os.path.join('media', 'chat_uploads', user_folder_name)
            if os.path.exists(user_upload_path):
                shutil.rmtree(user_upload_path)
                print(f"Cleaned up files for session {self.session_id}")
        except Exception as e:
            print(f"Error cleaning up files for session {self.session_id}: {e}")

    def save(self, *args, **kwargs):
        # If session is being deactivated, clean up files
        if self.pk:  # Only for existing objects
            old_instance = ChatSession.objects.get(pk=self.pk)
            if old_instance.is_active and not self.is_active:
                self.cleanup_user_files()
        super().save(*args, **kwargs)

    @classmethod
    def get_or_create_session(cls, user):
        """
        Get existing active session or create new one.
        Maintains maximum of 2 sessions per user.
        """
        # Get existing active sessions for this user
        existing_sessions = cls.objects.filter(
            user=user, 
            is_active=True
        ).order_by('-updated_at')
        
        # If user has active sessions, return the most recent one
        if existing_sessions.exists():
            session = existing_sessions.first()
            session.updated_at = timezone.now()  # Update last activity
            session.save()
            return session, False  # (session, created)
        
        # Check if user has reached maximum sessions
        total_sessions = cls.objects.filter(user=user).count()
        
        if total_sessions >= 2:
            # Deactivate the oldest session to make room for new one
            oldest_session = cls.objects.filter(user=user).order_by('created_at').first()
            if oldest_session:
                oldest_session.is_active = False
                oldest_session.save()
        
        # Create new session
        new_session = cls.objects.create(user=user)
        return new_session, True  # (session, created)

    @classmethod
    def get_user_sessions(cls, user):
        """
        Get all active sessions for a user
        """
        sessions = cls.objects.filter(user=user, is_active=True).order_by('-updated_at')
        
        session_list = []
        for session in sessions:
            session_list.append({
                'session_id': str(session.session_id),
                'created_at': session.created_at,
                'updated_at': session.updated_at,
                'message_count': session.messages.count()
            })
        
        return session_list


class ChatMessage(models.Model):
    SENDER_CHOICES = (('User', 'User'), ('AI', 'AI'))
    FLAG_CHOICES = (('Received from Adjuster', 'Received from Adjuster'), ('Sent to Adjuster', 'Sent to Adjuster'))

    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='chat_messages')
    sender = models.CharField(max_length=10, choices=SENDER_CHOICES)
    content = models.TextField()
    flagged = models.BooleanField(default=False)
    flag_type = models.CharField(max_length=30, choices=FLAG_CHOICES, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.sender}: {self.content[:30]}'


class FlaggedMessage(models.Model):
    message = models.OneToOneField(ChatMessage, on_delete=models.CASCADE, related_name="flagged_entry")
    flagged_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    flag_type = models.CharField(max_length=30, null=True, blank=True)
    flagged_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Flagged Message ID: {self.message.id} by {self.flagged_by.email}"


class UserClaimUpload(models.Model):
    """Model to store user's claim information and file uploads across devices"""
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='claim_uploads')
    upload_id = models.UUIDField(unique=True, editable=False, default=uuid.uuid4)
    
    # Claim information fields
    insurance_company_name = models.CharField(max_length=255, blank=True, null=True)
    policy_number = models.CharField(max_length=100, blank=True, null=True)
    police_report_number = models.CharField(max_length=100, blank=True, null=True)
    adjuster_name = models.CharField(max_length=255, blank=True, null=True)
    adjuster_phone_number = models.CharField(max_length=20, blank=True, null=True)
    add_claim_number = models.CharField(max_length=100, blank=True, null=True)
    adjuster_email = models.EmailField(blank=True, null=True)
    
    # File storage information
    upload_folder_path = models.CharField(max_length=500, blank=True, null=True)
    files_metadata = models.JSONField(default=list, blank=True)  # Store file information
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"Claim Upload {self.upload_id} - {self.user.email}"
    
    def get_claim_info_dict(self):
        """Return claim information as a dictionary, excluding empty values"""
        claim_info = {
            'insurance_company_name': self.insurance_company_name,
            'policy_number': self.policy_number,
            'police_report_number': self.police_report_number,
            'adjuster_name': self.adjuster_name,
            'adjuster_phone_number': self.adjuster_phone_number,
            'add_claim_number': self.add_claim_number,
            'adjuster_email': self.adjuster_email,
        }
        # Filter out empty values
        return {k: v for k, v in claim_info.items() if v and str(v).strip()}
    
    def update_claim_info(self, claim_data):
        """Update claim information from a dictionary"""
        for field, value in claim_data.items():
            if hasattr(self, field) and value and str(value).strip():
                setattr(self, field, value)
    
    def cleanup_files(self):
        """Clean up uploaded files when claim upload is deleted"""
        try:
            if self.upload_folder_path and os.path.exists(self.upload_folder_path):
                shutil.rmtree(self.upload_folder_path)
                print(f"Cleaned up files for claim upload {self.upload_id}")
        except Exception as e:
            print(f"Error cleaning up files for claim upload {self.upload_id}: {e}")
    
    def delete(self, *args, **kwargs):
        # Clean up files before deleting the record
        self.cleanup_files()
        super().delete(*args, **kwargs)