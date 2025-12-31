from django.urls import path
from . import views

urlpatterns = [
    path('', views.quiz_list, name='quiz_list'),
    path('categories/<slug:category_slug>/', views.subcategory_select, name='subcategory_select'),
    path('categories/<slug:category_slug>/start/', views.start_quiz, name='start_quiz'),
    path('<int:quiz_id>/take/', views.take_quiz, name='take_quiz'),
    path('attempt/<int:attempt_id>/result/', views.quiz_result, name='quiz_result'),
]
