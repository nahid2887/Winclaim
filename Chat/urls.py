from django.urls import path
from .views import (
    ChatStreamAPIView, FlagMessageAPIView, FlaggedMessagesListAPIView, 
    DownloadChatPDFAPIView, UserSessionsAPIView, FileUploadAPIView,
    ClaimUploadRetrieveUpdateAPIView, UserClaimUploadsListAPIView
)

urlpatterns = [
    path('chat/', ChatStreamAPIView.as_view(), name='chat-api'),
    path('chat/sessions/', UserSessionsAPIView.as_view(), name='user-sessions-api'),
    path("chat/flag/", FlagMessageAPIView.as_view(), name="flag-message"),
    path("chat/flagged/", FlaggedMessagesListAPIView.as_view(), name="flagged-messages"),
    path('chat/<uuid:session_id>/download-pdf/', DownloadChatPDFAPIView.as_view(), name='download_chat_pdf'),
    path('chat/upload/', FileUploadAPIView.as_view(), name='file-upload'),
    path('chat/uploads/', UserClaimUploadsListAPIView.as_view(), name='user-claim-uploads-list'),
    path('chat/uploads/<uuid:upload_id>/', ClaimUploadRetrieveUpdateAPIView.as_view(), name='claim-upload-detail'),
]
