from . import views

from rest_framework import routers

router = routers.DefaultRouter()
router.register("users", views.UserViewSet, basename="user")
router.register("teams", views.TeamViewSet, basename="team")
router.register("invitations", views.InvitationViewSet, basename="invitation")
router.register("join_requests", views.JoinRequestViewSet, basename="join_request")
router.register("apikeys", views.AccountAPIKeyViewSet, basename="apikey")

urlpatterns = router.urls
