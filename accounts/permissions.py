from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework import status
from .models import Profile
from subscription.models import UserSubscriptionModel


class IsTrialOrSubscriptionActive(BasePermission):
    """
    Custom permission class that allows access only if:
    1. User is authenticated AND
    2. User has active trial (is_trial_active=True) OR has active subscription (is_subscription=True or has_active_subscription=True)
    """
    
    message = "Access denied. You need an active trial or subscription to access this feature."
    
    def has_permission(self, request, view):
        # First check if user is authenticated
        if not request.user or not request.user.is_authenticated:
            self.message = "Authentication required."
            return False
        
        user = request.user
        
        try:
            # Get or create user profile
            profile, created = Profile.objects.get_or_create(user=user)
            
            # Check if trial is still active using the property
            if profile.is_trial_active:
                return True
            
            # Check if subscription is enabled in profile
            if profile.is_subscription:
                return True
            
            # Check if user has active paid subscription
            active_subscription = user.package.filter(is_active=True).first()
            if active_subscription:
                return True
            
            # If none of the above conditions are met, deny access
            self.message = "Your trial has expired and you don't have an active subscription. Please subscribe to continue using this feature."
            return False
            
        except Exception as e:
            # In case of any error, create profile with default trial
            Profile.objects.get_or_create(user=user)
            self.message = "Unable to verify subscription status. Please try again."
            return False


class IsTrialOrSubscriptionActiveWithResponse(BasePermission):
    """
    Enhanced permission class that provides detailed response about subscription status
    Use this for API endpoints that need to return subscription information
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        user = request.user
        
        try:
            profile, created = Profile.objects.get_or_create(user=user)
            
            # Collect subscription status information using the new property
            subscription_info = {
                'is_trial': profile.is_trial_active,  # Use property instead of field
                'is_subscription': profile.is_subscription,
                'has_active_subscription': bool(user.package.filter(is_active=True).first()),
                'trial_expired': not profile.is_trial_active,
                'subscription_required': not (profile.is_trial_active or profile.is_subscription or user.package.filter(is_active=True).exists())
            }
            
            # Store subscription info in request for use in views
            request.subscription_info = subscription_info
            
            # Allow access if any subscription condition is met
            return (profile.is_trial_active or 
                   profile.is_subscription or 
                   user.package.filter(is_active=True).exists())
            
        except Exception:
            return False


class IsDashboardAccessAllowed(BasePermission):
    """
    Specific permission for dashboard access
    Allows access to dashboard features like profile, settings, etc.
    """
    
    message = "Dashboard access requires an active trial or subscription."
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        user = request.user
        
        try:
            profile, created = Profile.objects.get_or_create(user=user)
            
            # Dashboard access conditions using the new property
            return (profile.is_trial_active or 
                   profile.is_subscription or 
                   user.package.filter(is_active=True).exists())
            
        except Exception:
            return False


class IsChatAccessAllowed(BasePermission):
    """
    Specific permission for chat features
    Stricter permission for AI chat functionality
    """
    
    message = "AI Chat access requires an active trial or subscription."
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        user = request.user
        
        try:
            profile, created = Profile.objects.get_or_create(user=user)
            
            # Chat access conditions using the new property
            return (profile.is_trial_active or 
                   profile.is_subscription or 
                   user.package.filter(is_active=True).exists())
            
        except Exception:
            return False


class IsSubscriptionRequired(BasePermission):
    """
    Strict permission that requires active paid subscription only
    Use for premium features that require actual payment
    """
    
    message = "This feature requires an active paid subscription."
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        user = request.user
        
        try:
            # Only allow if user has active paid subscription
            return user.package.filter(is_active=True).exists()
            
        except Exception:
            return False
