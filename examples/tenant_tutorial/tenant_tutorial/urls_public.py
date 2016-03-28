import django
from django.conf.urls import url
from tenant_tutorial.views import HomeView


urlpatterns = [
    url(r'^$', HomeView.as_view()),
]

if django.VERSION < (1, 9, 0):
    urlpatterns = django.conf.urls.patterns('', *urlpatterns)
