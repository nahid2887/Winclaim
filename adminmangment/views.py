# accounts/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from accounts.models import CustomUser, Profile
from .serializers import StaffViewUserSerializer,TotalRevenueSerializer , TermsaAndPolicySerializer
from django.shortcuts import get_object_or_404
from subscription.models import Total_revenue,UserSubscriptionModel
from decimal import Decimal
from rest_framework import generics, permissions
from userdashboard.models import InsuranceClaim
from .serializers import StaffInsuranceClaimSerializer ,TermsaAndconditionserializer
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from .models import TermsaAndPolicy, TermsaAndcondition
from datetime import datetime
from collections import OrderedDict
from django.db.models import Sum
from rest_framework import filters


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from django.db.models import Q
from django.db.models.functions import ExtractYear, ExtractMonth
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import CustomUser
from .serializers import StaffViewUserSerializer


class StaffOnlyUserList(APIView):
    """
    Admin‑only list of non‑staff users.
    • search   – partial match on name, email, or phone
    • sort_by  – signup_month | signup_year | subscription
    """
    permission_classes = [permissions.IsAdminUser]

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                "search", openapi.IN_QUERY,
                description="Partial match on full name, email, or phone",
                type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                "sort_by", openapi.IN_QUERY,
                description="signup_month | signup_year | subscription",
                type=openapi.TYPE_STRING,
                enum=["signup_month", "signup_year", "subscription"]
            ),
        ]
    )
    def get(self, request):
        search  = request.GET.get("search")
        sort_by = request.GET.get("sort_by")

        # preload profile to avoid N+1
        users = CustomUser.objects.filter(is_staff=False).select_related("profile").order_by("-date_joined")

        # ----- search -----
        if search:
            users = users.filter(
                Q(full_name__icontains=search) |
                Q(email__icontains=search)     |
                Q(phone_number__icontains=search)
            )

        # ----- sort -----
        if sort_by == "signup_month":
            users = users.annotate(
                month=ExtractMonth("date_joined")
            ).order_by("month")
        elif sort_by == "signup_year":
            users = users.annotate(
                year=ExtractYear("date_joined")
            ).order_by("year")
        elif sort_by == "subscription":
            users = users.order_by("-profile__is_subscription")

        ser = StaffViewUserSerializer(users, many=True, context={'request': request})
        return Response(ser.data)



class StaffOnlyUserDetail(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request, user_id):
        user = get_object_or_404(CustomUser, pk=user_id, is_staff=False)
        serializer = StaffViewUserSerializer(user, context={'request': request})
        return Response(serializer.data, status=200)

    def delete(self, request, user_id):
        user = get_object_or_404(CustomUser, pk=user_id, is_staff=False)
        user.delete()
        return Response({"detail": "User deleted."}, status=204)


class RevenueView(APIView):
    permission_classes = [permissions.IsAdminUser] 

    def get(self, request):
        currency = request.query_params.get('currency', 'usd').lower()  # default is USD

        try:
            revenue = Total_revenue.objects.first()
        except Total_revenue.DoesNotExist:
            return Response({"error": "Revenue data not found"}, status=404)

        

        if currency == 'cad':
            converted = revenue.total_revenue * Decimal('1.37')
            return Response({
                "currency": "CAD",
                "amount": round(converted, 2)
            })
        else:
            return Response({
                "currency": "USD",
                "amount": float(revenue.total_revenue)
            })


class StaffInsuranceClaimListView(APIView):
    """
    Admin-only list of insurance claims.
    • Single search box for:
        - User Name
        - Claim Type
    """
    permission_classes = [permissions.IsAdminUser]

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'search', openapi.IN_QUERY,
                description="Search by User Name or Claim Type (partial match)",
                type=openapi.TYPE_STRING
            ),
        ]
    )
    def get(self, request):
        search = request.GET.get('search')

        # Optimize DB access
        queryset = InsuranceClaim.objects.select_related('user', 'user__profile')

        # Apply search filter across multiple fields
        if search:
            queryset = queryset.filter(
                Q(user__full_name__icontains=search) |
                Q(type_of_claim__icontains=search)
            )

        serializer = StaffInsuranceClaimSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)
    
class StaffInsuranceClaimDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAdminUser]
    queryset = InsuranceClaim.objects.all()
    serializer_class = StaffInsuranceClaimSerializer

    @swagger_auto_schema(
        operation_summary="Retrieve a specific insurance claim",
        operation_description="Staff can view detailed information of a single insurance claim.",
        responses={200: StaffInsuranceClaimSerializer()}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Update insurance claim status",
        operation_description="Staff can update the status of an insurance claim.",
        request_body=StaffInsuranceClaimSerializer,
        responses={
            200: StaffInsuranceClaimSerializer(),
            400: "Validation error"
        }
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Delete an insurance claim",
        operation_description="Staff can delete an insurance claim.",
        responses={204: "Deleted successfully", 404: "Not found"}
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)

@swagger_auto_schema(
    methods=['POST'],
    request_body=TermsaAndPolicySerializer,
)
@api_view(['GET', 'POST', 'PUT'])
def terms_policy_views(request):
    user = request.user


    if request.method == 'GET':
        terms_policy = TermsaAndPolicy.objects.order_by('-created_at').first()
        if not terms_policy:  # Check if the object is None
            return Response({"message": "No terms and policies found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = TermsaAndPolicySerializer(terms_policy)  # Remove many=True for single object
        return Response(serializer.data)

    # Only staff users can create or update
    if not user.is_authenticated or not user.is_staff:
        return Response({"detail": "Only admin users can modify terms and policies."}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'POST':
        serializer = TermsaAndPolicySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=user, updated_by=user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'PUT':
        terms_policy = TermsaAndPolicy.objects.last()
        if not terms_policy:
            return Response({"message": "No policy found to update"}, status=status.HTTP_404_NOT_FOUND)

        serializer = TermsaAndPolicySerializer(terms_policy, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save(updated_by=user)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    


@swagger_auto_schema(
    methods=['POST'],
    request_body=TermsaAndconditionserializer,
)
@api_view(['GET', 'POST', 'PUT'])
def terms_policy_condition(request):
    user = request.user   

    if request.method == 'GET':
        terms_condition = TermsaAndcondition.objects.order_by('-created_at').first()
        if not terms_condition:  # Check if the object is None
            return Response({"message": "No terms and conditions found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = TermsaAndconditionserializer(terms_condition)  # Remove many=True for single object
        return Response(serializer.data)

    # Only staff users can create or update
    if not user.is_authenticated or not user.is_staff:
        return Response({"detail": "Only admin users can modify terms and policies."}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'POST':
        serializer = TermsaAndconditionserializer(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=user, updated_by=user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'PUT':
        terms_policy = TermsaAndcondition.objects.last()
        if not terms_policy:
            return Response({"message": "No policy found to update"}, status=status.HTTP_404_NOT_FOUND)

        serializer = TermsaAndconditionserializer(terms_policy, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save(updated_by=user)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    
    


@api_view(['GET'])
@permission_classes([IsAdminUser])
def monthly_subscriber_growth(request):
    year = int(request.query_params.get('year', datetime.now().year))
    data = OrderedDict()

    for month in range(1, 13):
        count = UserSubscriptionModel.objects.filter(
            package_start_date__year=year,
            package_start_date__month=month
        ).count()
        data[datetime(year, month, 1).strftime('%B')] = count

    return Response({
        "year": year,
        "monthly_subscriber_growth": data
    })


@api_view(['GET'])
@permission_classes([IsAdminUser])
def monthly_revenue_overview(request):
    year = int(request.query_params.get('year', datetime.now().year))
    data = OrderedDict()

    for month in range(1, 13):
        monthly_revenue = UserSubscriptionModel.objects.filter(
            package_start_date__year=year,
            package_start_date__month=month
        ).aggregate(total=Sum('package_amount'))['total'] or 0

        data[datetime(year, month, 1).strftime('%B')] = float(monthly_revenue)

    return Response({
        "year": year,
        "monthly_revenue_overview": data
    })



@api_view(['GET'])
@permission_classes([IsAdminUser])
def user_and_subscriber_count_view(request):
    total_users = CustomUser.objects.filter(is_superuser=False, is_staff=False).count()
    total_subscribers = Profile.objects.filter(is_subscription=True).count()

    return Response({
        "total_users": total_users,
        "total_subscribers": total_subscribers
    })
