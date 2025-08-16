from rest_framework import serializers
from .models import ChatSession, ChatMessage, FlaggedMessage, UserClaimUpload

class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = '__all__'
        read_only_fields = ('sender', 'timestamp', 'user', 'session')

class ChatSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatSession
        fields = ['session_id', 'created_at', 'updated_at', 'is_active']



class FlaggedMessageSerializer(serializers.ModelSerializer):
    message = ChatMessageSerializer(read_only=True)

    class Meta:
        model = FlaggedMessage
        fields = ['id', 'message', 'flagged_by', 'flag_type', 'flagged_at']


class UserClaimUploadSerializer(serializers.ModelSerializer):
    upload_id = serializers.UUIDField(read_only=True)
    files_count = serializers.SerializerMethodField()
    claim_fields_count = serializers.SerializerMethodField()

    class Meta:
        model = UserClaimUpload
        fields = [
            'upload_id', 'insurance_company_name', 'policy_number', 
            'police_report_number', 'adjuster_name', 'adjuster_phone_number',
            'add_claim_number', 'adjuster_email', 'upload_folder_path',
            'files_metadata', 'files_count', 'claim_fields_count',
            'created_at', 'updated_at', 'is_active'
        ]
        read_only_fields = ('upload_id', 'upload_folder_path', 'files_metadata', 'created_at', 'updated_at')

    def get_files_count(self, obj):
        return len(obj.files_metadata) if obj.files_metadata else 0

    def get_claim_fields_count(self, obj):
        return len(obj.get_claim_info_dict())
    


# class ClaimAnalysisSerializer(serializers.Serializer):
#     claim_no = serializers.IntegerField()
#     list_item = serializers.ListField(child=serializers.CharField())
#     name = serializers.CharField()
#     phone = serializers.CharField()
#     email = serializers.EmailField()
#     policy = serializers.FileField()
#     receipt = serializers.FileField()
