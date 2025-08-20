# accounts/urls.py or your main urls.py

from django.urls import path
from .views import StaffOnlyUserList, StaffOnlyUserDetail,RevenueView,StaffInsuranceClaimDetailView,StaffInsuranceClaimListView
from .views import terms_policy_views,monthly_revenue_overview,monthly_subscriber_growth,user_and_subscriber_count_view, terms_policy_condition

urlpatterns = [
    

    # Staff-only views
    path('admin/users/', StaffOnlyUserList.as_view(), name='staff-user-list'),
    path('admin/users/<str:user_id>/', StaffOnlyUserDetail.as_view(), name='staff-user-delete'),
    path('admin/revenue/', RevenueView.as_view(), name='admin-revenue'),
    path('admin/claims/', StaffInsuranceClaimListView.as_view(), name='admin-claim-list'),
    path('admin/claims/<int:pk>/', StaffInsuranceClaimDetailView.as_view(), name='admin-claim-detail'),
    path('privecy_policy/', terms_policy_views, name='terms-policy'),
    path('terms-condition/', terms_policy_condition, name='terms-condition'),
    path('admin/subscribers-growth/', monthly_subscriber_growth, name='monthly-subscriber-growth'),
    path('admin/revenue-overview/', monthly_revenue_overview, name='monthly-revenue-overview'),
    path('admin/user-stats/', user_and_subscriber_count_view, name='user-stats'),
]
