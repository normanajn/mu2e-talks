from django.urls import path

from . import views

app_name = 'api'

urlpatterns = [
    path('', views.ApiDocsView.as_view(), name='index'),
    path('tokens/<int:pk>/revoke/', views.ApiTokenRevokeView.as_view(), name='token-revoke'),
    path('v1/institutions/', views.InstitutionCreateApiView.as_view(), name='institution-create'),
    path('v1/conferences/', views.ConferenceCreateApiView.as_view(), name='conference-create'),
    path('v1/talks/', views.TalkCreateApiView.as_view(), name='talk-create'),
]
