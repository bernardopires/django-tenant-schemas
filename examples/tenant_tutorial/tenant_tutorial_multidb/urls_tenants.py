from customers.views import TenantView
from django.conf.urls import url, include


urlpatterns = [
     url(r'^(?P<db>\w+)/$', TenantView.as_view()),
     
]