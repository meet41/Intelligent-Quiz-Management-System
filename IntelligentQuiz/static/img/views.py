from django.shortcuts import render
from Quizez.models import Quiz, Category


def home(request):
	quizzes = Quiz.objects.filter(is_published=True).order_by('-created_at')[:6]
	categories = Category.objects.all()[:8]
	context = {
		'quizzes': quizzes,
		'categories': categories,
	}
	return render(request, 'dashboard/home.html', context)

# Create your views here.
