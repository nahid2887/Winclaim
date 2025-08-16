from django.urls import include, path
from  .views import subscription_update,CreateStripeSessionView,stripe_webhook, subscription_list_creat

urlpatterns = [
     path('subscription/', subscription_update, name='subscription-update'),
     path("stripe/payment/",CreateStripeSessionView.as_view()),
     path('webhook/', stripe_webhook, name='stripe-webhook'),
     path('subcriptionlist/',subscription_list_creat, name="subscription_list_creat" )
]