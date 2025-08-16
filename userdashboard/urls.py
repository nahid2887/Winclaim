from django.urls import path
from .views import InsuranceClaimListCreateView,ContactUsView, TemplateListAPIView

urlpatterns = [
   
    path('my-claims/', InsuranceClaimListCreateView.as_view(), name='list-claims'),
    path('contact-us/', ContactUsView.as_view(), name='contact-us'),
    path('templates/', TemplateListAPIView.as_view(), name='template-list'),
]