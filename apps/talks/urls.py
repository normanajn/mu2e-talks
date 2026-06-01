from django.urls import path

from . import views

app_name = 'talks'

urlpatterns = [
    path('', views.TalkListView.as_view(), name='list'),
    path('new/', views.TalkCreateView.as_view(), name='create'),
    path('conferences/', views.ConferenceListView.as_view(), name='conferences'),
    path('<int:pk>/', views.TalkDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.TalkUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', views.TalkDeleteView.as_view(), name='delete'),
    path('<int:pk>/activate/', views.TalkActivateView.as_view(), name='activate'),
    path('markdown-preview/', views.MarkdownPreviewView.as_view(), name='markdown-preview'),
]
