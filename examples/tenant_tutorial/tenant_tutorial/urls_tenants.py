from django.conf.urls import url
from customers.views import TenantView

urlpatterns = [
    url(r'^$', TenantView.as_view()),
]
