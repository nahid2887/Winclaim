from rest_framework import generics, status
from rest_framework.views import APIView 
from rest_framework.response import Response
from .serializers import CustomRegisterSerializer, CustomLoginSerializer, ForgotPasswordSerializer, OTPVerifySerializer, ResetPasswordSerializer, ChangePasswordSerializer,CustomUserSerializer,GoogleLoginSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.exceptions import ValidationError
from .models import CustomUser,Profile
from Chat.models import ChatSession, UserClaimUpload  # Import ChatSession model and UserClaimUpload
from subscription.models import UserSubscriptionModel  # Import subscription model
from rest_framework.decorators import api_view ,permission_classes,parser_classes
from drf_yasg.utils import swagger_auto_schema
from rest_framework.exceptions import ValidationError
from .utils import send_otp_email
import random
from django.utils import timezone
from datetime import timedelta  # Add this import
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from drf_yasg import openapi
from .permissions import IsDashboardAccessAllowed  # Import custom permission


def get_user_claim_uploads_info(user):
    """Helper function to get user's active claim uploads"""
    try:
        claim_uploads = UserClaimUpload.objects.filter(
            user=user, 
            is_active=True
        ).order_by('-updated_at')
        
        uploads_info = []
        for upload in claim_uploads[:5]:  # Limit to 5 most recent
            uploads_info.append({
                'upload_id': str(upload.upload_id),
                'created_at': upload.created_at.strftime('%Y-%m-%d') if upload.created_at else None,
                'updated_at': upload.updated_at.strftime('%Y-%m-%d') if upload.updated_at else None,
                'files_count': len(upload.files_metadata) if upload.files_metadata else 0,
                'claim_fields_count': len(upload.get_claim_info_dict()),
                'has_files': bool(upload.files_metadata),
                'has_claim_info': bool(upload.get_claim_info_dict())
            })
        
        return uploads_info
    except Exception as e:
        print(f"Error getting claim uploads for user {user.email}: {e}")
        return []


def get_user_subscription_info(user):
    """Helper function to get user subscription and trial information"""
    try:
        profile = user.profile
        is_trial = profile.is_trial_active  # Use the property instead of field
        is_subscription = profile.is_subscription
    except Profile.DoesNotExist:
        # Create profile if it doesn't exist
        profile = Profile.objects.create(user=user)
        is_trial = profile.is_trial_active  # Use the property
        is_subscription = profile.is_subscription
    
    # Check if user has active subscription
    try:
        user_subscription = user.package.filter(is_active=True).first()
        has_active_subscription = bool(user_subscription)
        subscription_type = user_subscription.package_type if user_subscription else None
    except:
        has_active_subscription = False
        subscription_type = None
    
    return {
        'is_trial': is_trial,
        'is_subscription': is_subscription,
        'has_active_subscription': has_active_subscription,
        'subscription_type': subscription_type,
        'signup_date': user.date_joined.strftime('%Y-%m-%d') if user.date_joined else None
    }


class CustomRegisterView(generics.CreateAPIView):
    serializer_class = CustomRegisterSerializer
    @swagger_auto_schema(
        operation_summary="Register a new user",
        operation_description="Signup using full name, email, mobile, and password.",
        request_body=CustomRegisterSerializer,
        responses={
            201: openapi.Response("User created successfully"),
            400: openapi.Response("Bad request (validation errors)")
        }
    )


    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)
            user = serializer.save()

            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)

            # Get subscription information
            subscription_info = get_user_subscription_info(user)
            
            # Get user's claim uploads information (will be empty for new users)
            claim_uploads_info = get_user_claim_uploads_info(user)

            return Response({
                "message": "Registration successful",
                "access": access_token,
                "refresh": refresh_token,
                "user": {
                    "pk": user.pk,
                    "email": user.email,
                    "full_name": user.full_name,
                    "signup_date": subscription_info['signup_date'],
                    "is_subscription": subscription_info['is_subscription'],
                    "is_trial": subscription_info['is_trial'],
                    "has_active_subscription": subscription_info['has_active_subscription'],
                    "subscription_type": subscription_info['subscription_type']
                },
                "claim_uploads": claim_uploads_info,
                "error": None
            }, status=status.HTTP_201_CREATED)

        except ValidationError as e:
            return Response({
                "message": "Registration failed",
                "error": e.detail
            }, status=status.HTTP_400_BAD_REQUEST)



class CustomLoginView(APIView):
    @swagger_auto_schema(
        operation_summary="Login",
        operation_description="Signup using full name, email, mobile, and password.",
        request_body= CustomLoginSerializer,
        responses={
            201: openapi.Response("User Login successfully"),
            400: openapi.Response("Bad request (validation errors)")
        }
    )
    def post(self, request):
        serializer = CustomLoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]

        refresh = RefreshToken.for_user(user)

        # Get user's chat sessions grouped by chat type
        user_sessions = ChatSession.get_user_sessions(user)
        
        # Get subscription information
        subscription_info = get_user_subscription_info(user)
        
        # Get user's claim uploads information
        claim_uploads_info = get_user_claim_uploads_info(user)

        return Response({
            "message": "Login successful",
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "pk": user.pk,
                "email": user.email,
                "full_name": user.full_name,
                "signup_date": subscription_info['signup_date'],
                "is_subscription": subscription_info['is_subscription'],
                "is_trial": subscription_info['is_trial'],
                "has_active_subscription": subscription_info['has_active_subscription'],
                "subscription_type": subscription_info['subscription_type']
            },
            "chat_sessions": user_sessions,
            "claim_uploads": claim_uploads_info,
            "error": None
        }, status=status.HTTP_200_OK)
    


@swagger_auto_schema(
    methods=['POST'],
    request_body=ForgotPasswordSerializer,
)
@api_view(['POST'])
def forgot_password_view(request):
    serializer = ForgotPasswordSerializer(data=request.data)
    if serializer.is_valid():
        email = serializer.validated_data['email']
        try:
            user = CustomUser.objects.get(email=email)
            otp = str(random.randint(100000, 999999))
            user.otp = otp
            user.otp_created_at = timezone.now()
            user.save()
            send_otp_email(user.email, otp)
            return Response({'message': 'OTP sent to email.'}, status=status.HTTP_200_OK)
        except CustomUser.DoesNotExist:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(
    methods=['POST'],
    request_body=OTPVerifySerializer,
)
@api_view(['POST'])
def verify_otp_view(request):
    serializer = OTPVerifySerializer(data=request.data)
    if serializer.is_valid():
        email = serializer.validated_data['email']
        otp = serializer.validated_data['otp']
        try:
            user = CustomUser.objects.get(email=email, otp=otp)
            if user.is_otp_valid():
                return Response({'message': 'OTP verified.'}, status=status.HTTP_200_OK)
            else:
                return Response({'error': 'OTP expired.'}, status=status.HTTP_400_BAD_REQUEST)
        except CustomUser.DoesNotExist:
            return Response({'error': 'Invalid email or OTP.'}, status=status.HTTP_404_NOT_FOUND)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@swagger_auto_schema(
    methods=['POST'],
    request_body=ResetPasswordSerializer,
)
@api_view(['POST'])
def reset_password_view(request):
    serializer = ResetPasswordSerializer(data=request.data)
    if serializer.is_valid():
        email = serializer.validated_data['email']
        otp = serializer.validated_data['otp']
        new_password = serializer.validated_data['new_password']
        try:
            user = CustomUser.objects.get(email=email, otp=otp)
            if user.is_otp_valid():
                user.set_password(new_password)
                user.otp = None
                user.otp_created_at = None
                user.save()
                return Response({'message': 'Password reset successful.'}, status=status.HTTP_200_OK)
            else:
                return Response({'error': 'OTP expired.'}, status=status.HTTP_400_BAD_REQUEST)
        except CustomUser.DoesNotExist:
            return Response({'error': 'Invalid email or OTP.'}, status=status.HTTP_404_NOT_FOUND)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@swagger_auto_schema(
    methods=['POST'],
    request_body=ChangePasswordSerializer,
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    user = request.user
    serializer = ChangePasswordSerializer(data=request.data)

    if serializer.is_valid():
        old_password = serializer.validated_data['old_password']
        new_password = serializer.validated_data['new_password']

        if not user.check_password(old_password):
            return Response({'error': 'Old password is incorrect'}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()

        return Response({'message': 'Password changed successfully'}, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



@api_view(['GET', 'PATCH'])
@permission_classes([IsDashboardAccessAllowed])
@parser_classes([MultiPartParser, FormParser])
def update_profile(request):
    user = request.user
    
    # Ensure user has a profile
    try:
        profile = user.profile
    except Profile.DoesNotExist:
        Profile.objects.create(user=user)
        profile = user.profile

    if request.method == 'GET':
        serializer = CustomUserSerializer(user, context={'request': request})
        # Get subscription information
        subscription_info = get_user_subscription_info(user)

        # Get user data and add subscription info to profile
        user_data = serializer.data
        if 'profile' not in user_data:
            user_data['profile'] = {}

        user_data['profile'].update({
            'signup_date': subscription_info['signup_date'],
            'is_subscription': subscription_info['is_subscription'],
            'is_trial': subscription_info['is_trial'],
            'has_active_subscription': subscription_info['has_active_subscription'],
            'subscription_type': subscription_info['subscription_type']
        })

        return Response({
            "message": "Profile retrieved successfully.",
            "user": user_data,
            "error": None
        }, status=status.HTTP_200_OK)

    elif request.method == 'PATCH':
        serializer = CustomUserSerializer(user, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            
            # Refresh the user instance from database to get updated profile
            user.refresh_from_db()
            if hasattr(user, 'profile'):
                user.profile.refresh_from_db()
            
            # Get subscription information for updated profile
            subscription_info = get_user_subscription_info(user)

            # Get updated user data with fresh serializer instance
            updated_serializer = CustomUserSerializer(user, context={'request': request})
            user_data = updated_serializer.data
            
            if 'profile' not in user_data:
                user_data['profile'] = {}

            user_data['profile'].update({
                'signup_date': subscription_info['signup_date'],
                'is_subscription': subscription_info['is_subscription'],
                'is_trial': subscription_info['is_trial'],
                'has_active_subscription': subscription_info['has_active_subscription'],
                'subscription_type': subscription_info['subscription_type']
            })

            return Response({
                "message": "Profile updated successfully.",
                "user": user_data,
                "error": None
            }, status=status.HTTP_200_OK)
        return Response({
            "message": "Profile update failed.",
            "error": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_subscription_status(request):
    """
    API endpoint to check user's subscription status
    This endpoint doesn't require trial/subscription - it's used to check status
    """
    user = request.user
    subscription_info = get_user_subscription_info(user)
    
    # Get detailed trial information
    try:
        profile = user.profile
        trial_days_left = 0
        if profile.is_trial_active and profile.created_at:
            trial_expiry = profile.created_at + timedelta(days=3)
            days_left = (trial_expiry - timezone.now()).days
            trial_days_left = max(0, days_left)
    except Profile.DoesNotExist:
        trial_days_left = 3  # New profile will have 3 days
    
    return Response({
        "message": "Subscription status retrieved successfully",
        "subscription_info": subscription_info,
        "trial_days_left": trial_days_left,
        "access_granted": {
            "dashboard_access": subscription_info['is_trial'] or subscription_info['is_subscription'] or subscription_info['has_active_subscription'],
            "chat_access": subscription_info['is_trial'] or subscription_info['is_subscription'] or subscription_info['has_active_subscription'],
            "premium_features": subscription_info['has_active_subscription']
        }
    }, status=status.HTTP_200_OK)
    


class GoogleLoginAPIView(APIView):
    def post(self, request):
        serializer = GoogleLoginSerializer(data=request.data)
        if serializer.is_valid():
            user, created = serializer.save()

            refresh = RefreshToken.for_user(user)

            # Get user's chat sessions grouped by chat type
            user_sessions = ChatSession.get_user_sessions(user)
            
            # Get subscription information
            subscription_info = get_user_subscription_info(user)
            
            # Get user's claim uploads information
            claim_uploads_info = get_user_claim_uploads_info(user)

            return Response({
                'user_id': user.user_id,
                'email': user.email,
                'full_name': user.full_name,
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'is_new_user': created,  # ⬅️ ✅ new key in the response
                'chat_sessions': user_sessions,
                'claim_uploads': claim_uploads_info,
                'user': {
                    'pk': user.user_id,
                    'email': user.email,
                    'full_name': user.full_name,
                    'signup_date': subscription_info['signup_date'],
                    'is_subscription': subscription_info['is_subscription'],
                    'is_trial': subscription_info['is_trial'],
                    'has_active_subscription': subscription_info['has_active_subscription'],
                    'subscription_type': subscription_info['subscription_type']
                }
            }, status=200)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)