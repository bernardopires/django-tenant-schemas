from django.conf.urls import url
from tenant_tutorial.views import HomeView


urlpatterns = [
     url(r'^(?P<db>\w+)/$', HomeView.as_view()),
]