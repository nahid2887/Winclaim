from rest_framework import serializers
from django.core.exceptions import ValidationError
from .models import CustomUser, Profile
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth import get_user_model
import os
import logging

logger = logging.getLogger(__name__)



class CustomRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, min_length=8)

    class Meta:
        model = CustomUser
        fields = ['email', 'full_name', 'address', 'phone_number', 'password']

    def validate_password(self, value):
        # Ensure password is at least 8 characters long
        if len(value) < 8:
            raise ValidationError("Password must be at least 8 characters.")
        return value

    def create(self, validated_data):
        # Create a new user instance
        user = CustomUser(
            email=validated_data['email'],
            full_name=validated_data['full_name'],
            address=validated_data.get('address'),
            phone_number=validated_data.get('phone_number'),
        )
        user.set_password(validated_data['password'])
        user.save()
        # Ensure profile is created with is_trial=True (default)
        from .models import Profile
        Profile.objects.get_or_create(user=user, defaults={"is_trial": True})
        return user




User = get_user_model()

class CustomLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            raise AuthenticationFailed("Both email and password are required.")

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise AuthenticationFailed("Invalid email or password.")

        if not user.check_password(password):
            raise AuthenticationFailed("Invalid email or password.")

        if not user.is_active:
            raise AuthenticationFailed("User account is disabled.")

        data['user'] = user
        return data
    


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

class OTPVerifySerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)

class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)
    new_password = serializers.CharField(min_length=8, write_only=True)
    confirm_password = serializers.CharField(min_length=8, write_only=True)

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError("New password and confirm password do not match.")
        return data


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)
    confirm_password = serializers.CharField(required=True)

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError("New password and confirm password must match.")
        return data
    


class ProfileSerializer(serializers.ModelSerializer):
    profile_image = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = Profile
        fields = ['bio', 'profile_image', 'is_trial', 'is_subscription']
    
    def to_representation(self, instance):
        """Override to return absolute URL for profile image with cache busting"""
        data = super().to_representation(instance)
        if instance.profile_image:
            request = self.context.get('request')
            base_url = instance.profile_image.url
            
            # Add cache busting parameter based on file modification time
            try:
                import time
                import os
                if os.path.exists(instance.profile_image.path):
                    mtime = int(os.path.getmtime(instance.profile_image.path))
                    cache_buster = f"?v={mtime}"
                else:
                    cache_buster = f"?v={int(time.time())}"
            except:
                import time
                cache_buster = f"?v={int(time.time())}"
            
            if request:
                data['profile_image'] = request.build_absolute_uri(base_url) + cache_buster
            else:
                data['profile_image'] = base_url + cache_buster
        else:
            data['profile_image'] = None
        return data

class CustomUserSerializer(serializers.ModelSerializer):


    profile = ProfileSerializer()
    date_joined = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)

    class Meta:
        model = CustomUser
        fields = ['email', 'full_name', 'address', 'phone_number', 'profile', 'date_joined']

    def to_representation(self, instance):
        # Ensure profile exists before serialization
        if not hasattr(instance, 'profile') or instance.profile is None:
            Profile.objects.create(user=instance)
        data = super().to_representation(instance)
        # Add signup_date with time (for API response compatibility)
        data["signup_date"] = data["date_joined"]
        return data

    def update(self, instance, validated_data):
        profile_data = validated_data.pop('profile', None)

        # Update user fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Ensure profile exists
        try:
            profile = instance.profile
        except Profile.DoesNotExist:
            profile = Profile.objects.create(user=instance)

        # Update profile fields, including image
        if profile_data:
            # Handle profile image update
            if 'profile_image' in profile_data:
                new_image = profile_data['profile_image']
                logger.info(f"Updating profile image for user {instance.email}: {new_image}")
                
                # Delete old image if a new one is provided
                if new_image and profile.profile_image:
                    old_image_path = profile.profile_image.path
                    try:
                        if os.path.exists(old_image_path):
                            os.remove(old_image_path)
                            logger.info(f"Deleted old profile image: {old_image_path}")
                    except Exception as e:
                        logger.warning(f"Failed to delete old image {old_image_path}: {e}")
                
                # Set the new image (or None if clearing)
                profile.profile_image = new_image
            
            # Update other profile fields
            for attr, value in profile_data.items():
                if attr != 'profile_image':  # Already handled above
                    setattr(profile, attr, value)
            
            profile.save()
            logger.info(f"Profile updated successfully for user {instance.email}")

        return instance
    

        
class GoogleLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    full_name = serializers.CharField(max_length=255)

    def validate_email(self, value):
        if not value:
            raise serializers.ValidationError("Email is required.")
        return value

    def validate_full_name(self, value):
        if not value:
            raise serializers.ValidationError("Full name is required.")
        return value

    def create(self, validated_data):
        email = validated_data['email']
        full_name = validated_data['full_name']

        user, created = CustomUser.objects.get_or_create(
            email=email,
            defaults={'full_name': full_name}
        )

        from .models import Profile
        profile, prof_created = Profile.objects.get_or_create(user=user, defaults={"is_trial": True})
        # If user was just created, ensure is_trial is True
        if created or prof_created:
            profile.is_trial = True
            profile.save(update_fields=["is_trial"])

        # Return user and is_trial status
        return user, profile.is_trial