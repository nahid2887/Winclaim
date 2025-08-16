# accounts/serializers.py

from rest_framework import serializers
from accounts.models import CustomUser, Profile
from subscription.models import UserSubscriptionModel, Total_revenue
from accounts.serializers import ProfileSerializer
from userdashboard.models import InsuranceClaim
from .models import TermsaAndPolicy, TermsaAndcondition





class StaffInsuranceClaimSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    full_name = serializers.CharField(source='user.full_name', read_only=True)
    profile_image = serializers.SerializerMethodField()

    class Meta:
        model = InsuranceClaim
        fields = [
            'id',
            'user_email',
            'full_name',
            'profile_image',
            'type_of_claim',
            'description',
            'date_of_incident',
            'country_of_incident',
            'city_of_incident',
        ]

    def get_profile_image(self, obj):
        request = self.context.get('request')
        if obj.user.profile.profile_image and request:
            return request.build_absolute_uri(obj.user.profile.profile_image.url)
        return None

class UserSubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSubscriptionModel
        fields = ['package_type', 'is_active', 'package_start_date', 'package_end_date', 'package_amount']

class StaffViewUserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(read_only=True)
    package = UserSubscriptionSerializer(many=True, read_only=True)  # related_name='package' in your model

    class Meta:
        model = CustomUser
        fields = ['user_id', 'email', 'full_name', 'phone_number', 'date_joined', 'profile', 'package']





class TotalRevenueSerializer(serializers.ModelSerializer):
    total_revenue_cad = serializers.SerializerMethodField()

    class Meta:
        model = Total_revenue
        fields = ['total_revenue_usd', 'total_revenue_cad']

    def get_total_revenue_cad(self, obj):
        return round(obj.total_revenue_usd * 1.37, 2)
    







class TermsaAndPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = TermsaAndPolicy
        fields = ['id', 'title', 'content', 'created_at', 'updated_at', 'created_by', 'updated_by']
        read_only_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']


class TermsaAndconditionserializer(serializers.ModelSerializer):
    class Meta:
        model = TermsaAndcondition
        fields = ['id', 'title', 'content', 'created_at', 'updated_at', 'created_by', 'updated_by']
        read_only_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']