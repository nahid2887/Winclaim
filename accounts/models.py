from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone
from datetime import timedelta
import shortuuid


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email must be set')
        email = self.normalize_email(email)
        extra_fields.setdefault('is_active', True)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True')

        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractUser):
    # 🚫 Remove the default username field
    username = None

    user_id = models.CharField(
        max_length=30,
        unique=True,
        default=shortuuid.uuid,
        primary_key=True,
    )
    full_name = models.CharField(max_length=255, null=True, blank=True)
    email = models.EmailField(unique=True, db_index=True)
    address = models.CharField(max_length=255, null=True, blank=True)
    phone_number = models.CharField(max_length=15, null=True, blank=True)
    otp = models.CharField(null=True, blank=True, max_length=6)
    otp_created_at = models.DateTimeField(null=True, blank=True)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'  # 👈 required
    REQUIRED_FIELDS = ['full_name']

    def is_otp_valid(self):
        return self.otp and self.otp_created_at and timezone.now() <= self.otp_created_at + timedelta(minutes=10)



class Profile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(blank=True, null=True)
    profile_image = models.ImageField(upload_to='profile_images/', null=True, blank=True)
    is_trial = models.BooleanField(default=True)
    is_subscription = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def is_trial_active(self):
        """
        Check if trial is still active based on creation date
        Returns True only if is_trial=True AND within 3 days of creation
        """
        if not self.is_trial:
            return False
        
        if self.created_at:
            trial_expiry = self.created_at + timedelta(days=3)
            if timezone.now() > trial_expiry:
                # Auto-update the field if trial has expired
                self.is_trial = False
                self.save(update_fields=['is_trial'])
                return False
            return True
        return False

    def save(self, *args, **kwargs):
        # Automatically disable is_trial after 3 days
        if self.created_at and timezone.now() > self.created_at + timedelta(days=3):
            self.is_trial = False
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.email} - Trial: {self.is_trial_active} - Subscription: {self.is_subscription}"

        