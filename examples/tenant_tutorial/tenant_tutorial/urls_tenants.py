import django
from django.conf.urls import url
from customers.views import TenantView


urlpatterns = [
    url(r'^$', TenantView.as_view()),
]

if django.VERSION < (1, 9, 0):
    urlpatterns = django.conf.urls.patterns('', *urlpatterns)
