from customers.views import TenantView
from django.conf.urls import url

urlpatterns = [
    url(r'^$', TenantView.as_view()),
]
