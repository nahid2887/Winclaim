from rest_framework import serializers

from .models import SubscriptionModel,UserSubscriptionModel


class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionModel
        fields = "__all__"
        
        
class UserSubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSubscriptionModel
        fields = ["package_type","is_active","package_start_date","package_end_date","package_amount"]