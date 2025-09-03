from django.urls import path
from tenant_tutorial.views import HomeView


urlpatterns = [
    path('', HomeView.as_view()),
]
