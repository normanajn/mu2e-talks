from django.urls import path

from . import views

app_name = 'talks'

urlpatterns = [
    path('', views.TalkListView.as_view(), name='list'),
    path('new/', views.TalkCreateView.as_view(), name='create'),
    path('import-spreadsheet/', views.TalkSpreadsheetImportView.as_view(), name='spreadsheet-import'),
    path('conferences/', views.ConferenceListView.as_view(), name='conferences'),
    path('conferences/import/', views.ConferenceImportView.as_view(), name='conference-import'),
    path('conferences/new/', views.ConferenceCreateView.as_view(), name='conference-create'),
    path('conferences/<int:pk>/edit/', views.ConferenceUpdateView.as_view(), name='conference-edit'),
    path('conferences/<int:pk>/delete/', views.ConferenceDeleteView.as_view(), name='conference-delete'),
    path('<int:pk>/', views.TalkDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.TalkUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', views.TalkDeleteView.as_view(), name='delete'),
    path('<int:pk>/activate/', views.TalkActivateView.as_view(), name='activate'),
    path('markdown-preview/', views.MarkdownPreviewView.as_view(), name='markdown-preview'),
]
