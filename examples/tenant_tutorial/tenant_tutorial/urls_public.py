from django.conf.urls import patterns
from tenant_tutorial.views import HomeView

urlpatterns = patterns('',
   (r'^$', HomeView.as_view()),
)
