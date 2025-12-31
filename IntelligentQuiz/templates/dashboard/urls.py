from django.urls import path
from . import views

urlpatterns = [
    path('', views.quiz_list, name='quiz_list'),
    path('categories/<slug:category_slug>/', views.subcategory_select, name='subcategory_select'),
    path('categories/<slug:category_slug>/start/', views.start_quiz, name='start_quiz'),
    path('categories/<slug:category_slug>/generate-ai/', views.generate_ai_quiz, name='generate_ai_quiz'),
    # New session-based quiz taking (one question per page)
    path('<int:quiz_id>/session/', views.quiz_session, name='quiz_session'),
    path('<int:quiz_id>/take/', views.take_quiz, name='take_quiz'),
    path('attempt/<int:attempt_id>/result/', views.quiz_result, name='quiz_result'),
    # AI explanations
    path('answers/<int:answer_id>/explanation/', views.answer_explanation, name='answer_explanation'),
]
