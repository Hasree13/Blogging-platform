from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view),
    path('login/', views.login_view),
    path('register/', views.register),
    path('profile/', views.profile),
    path('logout/', views.logout_view),
    path('update_categories/', views.update_categories),
    path('toggle-author/', views.toggle_author),
    path('update_avatar/', views.update_avatar),
    path('edit-profile/', views.edit_profile, name='edit_profile'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
]