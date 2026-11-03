from django.urls import path
from .views import (
    BusinessRequestView,
    AnalyticsView,
    PolicyChatView,
    LogoutView,
    LoginView,
    RegisterView,
)

urlpatterns = [
    path("", BusinessRequestView.as_view(), name="request-list-create"),
    path("<int:id>/", BusinessRequestView.as_view(), name="request-detail"),
    path("analytics/", AnalyticsView.as_view(), name="request-analytics"),
    path("chat/", PolicyChatView.as_view(), name="policy-chat"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("login/", LoginView.as_view(), name="login"),
    path("register/", RegisterView.as_view(), name="register"),
]