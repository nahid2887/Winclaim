from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from .models import CustomUser, Profile
import os

@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(pre_save, sender=Profile)
def delete_old_profile_image(sender, instance, **kwargs):
    """Delete old profile image when a new one is uploaded"""
    if not instance.pk:
        return  # New instance, no old image to delete

    try:
        old_instance = Profile.objects.get(pk=instance.pk)
        if old_instance.profile_image and old_instance.profile_image != instance.profile_image:
            # Delete the old image file
            if os.path.exists(old_instance.profile_image.path):
                os.remove(old_instance.profile_image.path)
    except Profile.DoesNotExist:
        pass


@receiver(post_delete, sender=Profile)
def delete_profile_image_on_delete(sender, instance, **kwargs):
    """Delete profile image when profile is deleted"""
    if instance.profile_image:
        try:
            if os.path.exists(instance.profile_image.path):
                os.remove(instance.profile_image.path)
        except Exception:
            pass
