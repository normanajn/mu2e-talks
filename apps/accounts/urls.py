from django.urls import path

from . import views

urlpatterns = [
    path('preview-role/',  views.RolePreviewView.as_view(),  name='preview-role'),
    path('select-group/', views.GroupSelectionView.as_view(), name='select-group'),
    path('select-institution/', views.InstitutionSelectionView.as_view(), name='select-institution'),
    path('merge-roster/', views.RosterMergeView.as_view(), name='merge-roster'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('institutions/', views.InstitutionListView.as_view(), name='institutions'),
    path('institutions/<int:pk>/update/', views.InstitutionUpdateView.as_view(), name='institution-update'),
    path('institutions/<int:pk>/edit/', views.InstitutionEditView.as_view(), name='institution-edit'),
    path('admin-users/', views.AdminUsersView.as_view(), name='admin-users'),
    path('admin-users/import/', views.RosterImportView.as_view(), name='roster-import'),
    path('admin-users/create/',                  views.AdminCreateUserView.as_view(), name='user-create'),
    path('admin-users/signup-toggle/',           views.SignupToggleView.as_view(),    name='signup-toggle'),
    path('admin-users/<int:pk>/role/',           views.UserRoleUpdateView.as_view(),          name='user-role-update'),
    path('admin-users/<int:pk>/primary-group/',    views.UserPrimaryGroupView.as_view(),    name='user-primary-group'),
    path('admin-users/<int:pk>/managed-groups/',   views.UserManagedGroupsView.as_view(),   name='user-managed-groups'),
    path('admin-users/<int:pk>/managed-projects/', views.UserManagedProjectsView.as_view(), name='user-managed-projects'),
    path('admin-users/<int:pk>/set-password/',   views.UserSetPasswordView.as_view(), name='user-set-password'),
    path('admin-users/<int:pk>/edit/',           views.UserUpdateView.as_view(),      name='user-edit'),
    path('admin-users/<int:pk>/delete/',         views.UserDeleteView.as_view(),      name='user-delete'),
]
