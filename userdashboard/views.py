# claims/views.py

from rest_framework import generics, permissions
from .models import InsuranceClaim, Template
from .serializers import InsuranceClaimSerializer,ContactSerializer,TemplateSerializer
from drf_yasg.utils import swagger_auto_schema
from drf_yasg  import openapi
# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.mail import send_mail
from django.conf import settings
from accounts.permissions import IsDashboardAccessAllowed  # Import custom permission


class InsuranceClaimListCreateView(generics.ListCreateAPIView):
    serializer_class = InsuranceClaimSerializer
    permission_classes = [IsDashboardAccessAllowed]

    def get_queryset(self):
        # Users can only access their own claims
        return InsuranceClaim.objects.filter(user=self.request.user).order_by('-id')

    def perform_create(self, serializer):
        # Automatically assign the user
        serializer.save(user=self.request.user)

    @swagger_auto_schema(
        operation_summary="Submit a new insurance claim",
        operation_description="Create an insurance claim with type, incident details. User is automatically assigned from authentication token. Do not include user field in request body.",
        request_body=InsuranceClaimSerializer,
        responses={
            201: openapi.Response("Claim created successfully", InsuranceClaimSerializer),
            400: openapi.Response("Bad request (validation errors)")
        }
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

class TemplateListAPIView(generics.ListAPIView):
    queryset = Template.objects.all()
    serializer_class = TemplateSerializer


class ContactUsView(APIView):
    @swagger_auto_schema(
        operation_summary="Contact With Us ",
        operation_description="Full name., Email, Country ",
        request_body=ContactSerializer,
        responses={
            201: openapi.Response("User created successfully"),
            400: openapi.Response("Bad request (validation errors)")
        }
    )

    def post(self, request):
        serializer = ContactSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            subject = f"New Contact Us Message from {data['first_name']} {data['last_name']}"
            message = f"""
You received a new message from your Contact Us form:

Name: {data['first_name']} {data['last_name']}
Country: {data['country']}
Email: {data['email']}
Message:
{data['message']}
"""
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [settings.DEFAULT_FROM_EMAIL],  # Send to yourself
                fail_silently=False,
            )
            return Response({"message": "Your message has been sent successfully."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
