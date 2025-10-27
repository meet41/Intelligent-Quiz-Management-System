from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages

from .models import Quiz, Question, Choice, Attempt, Answer, Category


def quiz_list(request):
    categories = Category.objects.all()
    category_id = request.GET.get('category')
    
    quizzes = Quiz.objects.filter(is_published=True)
    if category_id:
        quizzes = quizzes.filter(category_id=category_id)
    quizzes = quizzes.order_by('-created_at')
    
    return render(request, 'quizez/quiz_list.html', {
        'quizzes': quizzes,
        'categories': categories,
        'current_category': category_id
    })


@login_required
@transaction.atomic
def take_quiz(request, quiz_id: int):
	quiz = get_object_or_404(Quiz, pk=quiz_id, is_published=True)
	questions = quiz.questions.prefetch_related('choices').all()

	if request.method == 'POST':
		attempt = Attempt.objects.create(user=request.user, quiz=quiz)

		score = 0
		total = questions.count()
		for q in questions:
			choice_id = request.POST.get(f'question_{q.id}')
			selected = None
			if choice_id:
				try:
					selected = q.choices.get(id=int(choice_id))
				except (ValueError, Choice.DoesNotExist):
					selected = None
			ans = Answer.objects.create(attempt=attempt, question=q, selected_choice=selected)
			if ans.is_correct():
				score += 1
		attempt.score = score
		attempt.total = total
		attempt.save()
		messages.success(request, f'Quiz submitted! You scored {score} out of {total}.')
		return redirect('quiz_result', attempt_id=attempt.id)

	return render(request, 'quizez/take_quiz.html', {
		'quiz': quiz,
		'questions': questions,
	})


@login_required
def quiz_result(request, attempt_id: int):
	attempt = get_object_or_404(Attempt.objects.select_related('quiz', 'user'), pk=attempt_id, user=request.user)
	answers = attempt.answers.select_related('question', 'selected_choice').all()
	return render(request, 'quizez/quiz_result.html', {
		'attempt': attempt,
		'answers': answers,
	})

# Create your views here.
