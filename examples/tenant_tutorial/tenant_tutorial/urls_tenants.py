from customers.views import TenantView
from django.urls import path

urlpatterns = [
    path('', TenantView.as_view()),
]
