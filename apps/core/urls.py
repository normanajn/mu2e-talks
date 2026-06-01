from django.urls import path

from . import views

urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('about/', views.AboutView.as_view(), name='about'),
    path('bug-report/', views.BugReportView.as_view(), name='bug-report'),
    path('bug-report/submit/', views.BugReportSubmitView.as_view(), name='bug-report-submit'),
]
