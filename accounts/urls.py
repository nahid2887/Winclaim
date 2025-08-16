from django.urls import path
from .views import CustomRegisterView, CustomLoginView ,GoogleLoginAPIView, forgot_password_view , verify_otp_view , reset_password_view , change_password,update_profile, check_subscription_status

urlpatterns = [
    path('register/', CustomRegisterView.as_view(), name='register'),
    path('login/', CustomLoginView.as_view(), name='custom-login'),
    path('forgot-password/', forgot_password_view, name='forgot-password'),
    path('verify-otp/', verify_otp_view, name='verify-otp'),
    path('reset-password/', reset_password_view, name='reset-password'),
    path('change-password/', change_password, name='change_password'),
    path('update-profile/', update_profile, name='update-profile'),
    path('subscription-status/', check_subscription_status, name='subscription-status'),
    path('auth/google-login/', GoogleLoginAPIView.as_view(), name='google-login'),
]
