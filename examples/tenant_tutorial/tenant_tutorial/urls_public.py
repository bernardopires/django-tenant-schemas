from django.conf.urls import url
from tenant_tutorial.views import HomeView

urlpatterns = [
    url(r'^$', HomeView.as_view()),
]
