from django.conf.urls import patterns
from customers.views import TenantView

urlpatterns = patterns('',
   (r'^$', TenantView.as_view()),
)