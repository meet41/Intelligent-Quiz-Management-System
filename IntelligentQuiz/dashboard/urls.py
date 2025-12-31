from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('history/', views.quiz_history, name='quiz_history'),
    path('stats/', views.dashboard_stats, name='dashboard_stats'),
    path('leaderboard/', views.leaderboard, name='leaderboard'),
]
