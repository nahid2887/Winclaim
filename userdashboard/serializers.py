# claims/serializers.py
from rest_framework import serializers
from .models import InsuranceClaim , Template

class InsuranceClaimSerializer(serializers.ModelSerializer):
    class Meta:
        model = InsuranceClaim
        fields = [
            'id',
            'type_of_claim',
            'description',
            'date_of_incident',
            'country_of_incident',
            'city_of_incident',
        ]
        read_only_fields = ['id']
        # Explicitly exclude user field since it's auto-assigned from token
       



class ContactSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    country = serializers.CharField(max_length=100)
    email = serializers.EmailField()
    message = serializers.CharField(style={'base_template': 'textarea.html'})

class TemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Template
        fields = '__all__'