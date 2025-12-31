from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.http import JsonResponse, HttpResponseNotAllowed

from .models import Quiz, Question, Choice, Attempt, Answer, Category, Subcategory, AIQuestionDraft, Explanation
from .services.ai_generation import generate_questions, generate_explanation


def quiz_list(request):
	categories = Category.objects.all()
	category_id = request.GET.get('category')

	quizzes = Quiz.objects.filter(is_published=True)
	if category_id:
		quizzes = quizzes.filter(category_id=category_id)
	quizzes = quizzes.order_by('-created_at')
	# Track which quizzes the current user has attempted
	attempted_ids = set()
	if request.user.is_authenticated:
		attempted_ids = set(Attempt.objects.filter(user=request.user).values_list('quiz_id', flat=True))

	return render(request, 'quizez/quiz_list.html', {
		'quizzes': quizzes,
		'categories': categories,
		'current_category': category_id,
		'attempted_ids': attempted_ids,
	})


def subcategory_select(request, category_slug: str):
	"""Display subcategories for a given category with difficulty and question count options."""
	category = get_object_or_404(Category, slug=category_slug)
	q = request.GET.get('q', '').strip()
	subcategories = category.subcategories.all().order_by('name')
	if q:
		subcategories = subcategories.filter(name__icontains=q)

	# Defaults
	difficulties = [
		(Quiz.DIFFICULTY_EASY, 'Easy'),
		(Quiz.DIFFICULTY_MEDIUM, 'Medium'),
		(Quiz.DIFFICULTY_HARD, 'Hard'),
	]
	question_options = [5, 10, 15, 20]

	return render(request, 'quizez/subcategory_select.html', {
		'category': category,
		'subcategories': subcategories,
		'q': q,
		'difficulties': difficulties,
		'question_options': question_options,
		'has_subcategories': category.subcategories.exists(),
	})


@login_required
def start_quiz(request, category_slug: str):
	"""Validate selection and hand off to generation step (to be implemented in Task 2.3)."""
	if request.method != 'POST':
		messages.error(request, 'Please select a subcategory and options to start a quiz.')
		return redirect('subcategory_select', category_slug=category_slug)

	category = get_object_or_404(Category, slug=category_slug)
	subcategory_id = request.POST.get('subcategory')
	difficulty = request.POST.get('difficulty')
	num_questions = request.POST.get('num_questions')

	# Validate inputs
	has_subcats = category.subcategories.exists()
	subcategory = None
	if subcategory_id:
		try:
			subcategory = Subcategory.objects.get(id=int(subcategory_id), category=category)
		except Exception:
			subcategory = None

	valid_difficulties = {Quiz.DIFFICULTY_EASY, Quiz.DIFFICULTY_MEDIUM, Quiz.DIFFICULTY_HARD}
	valid_counts = {'5', '10', '15', '20'}
	errors = []
	if has_subcats and not subcategory:
		errors.append('Please choose a subcategory.')
	if difficulty not in valid_difficulties:
		errors.append('Please choose a difficulty level.')
	if num_questions not in valid_counts:
		errors.append('Please choose a valid number of questions.')

	if errors:
		for e in errors:
			messages.error(request, e)
		# Preserve search query if present
		url = reverse('subcategory_select', kwargs={'category_slug': category_slug})
		return redirect(url)

	# Store selection for the generation step (Task 2.3)
	request.session['pending_quiz_request'] = {
		'category_slug': category.slug,
		'subcategory_id': (subcategory.id if subcategory else None),
		'difficulty': difficulty,
		'num_questions': int(num_questions),
		'user_id': request.user.id,
	}

	if subcategory:
		label = f"{category.name} / {subcategory.name}"
	else:
		label = category.name
	messages.success(request, f"Starting quiz generation for {label} - {difficulty.title()} • {num_questions} questions.")
	# For now, send the user back to quiz list; Task 2.3 will pick from the session and generate.
	return redirect('generate_ai_quiz', category_slug=category_slug)


@login_required
def generate_ai_quiz(request, category_slug: str):
	"""Generate AI questions from the pending selection and store as AIQuestionDraft for admin review."""
	data = request.session.get('pending_quiz_request') or {}
	category = get_object_or_404(Category, slug=category_slug)
	subcategory = None
	if data.get('subcategory_id'):
		try:
			subcategory = Subcategory.objects.get(id=int(data['subcategory_id']), category=category)
		except Exception:
			subcategory = None
	# Allow category-only flow when this category has no subcategories
	if not subcategory and category.subcategories.exists():
		messages.error(request, 'No pending quiz request found. Please select options again.')
		return redirect('subcategory_select', category_slug=category_slug)

	topic = f"{category.name} - {subcategory.name}" if subcategory else category.name
	difficulty = data.get('difficulty') or Quiz.DIFFICULTY_MEDIUM
	num_questions = int(data.get('num_questions') or 5)

	try:
		result = generate_questions(topic=topic, difficulty=difficulty, num_questions=num_questions)
		draft = AIQuestionDraft.objects.create(
			provider=result['provider'],
			prompt=result['prompt'],
			raw_response=result['raw'],
			parsed=result['parsed'],
			category=category,
			subcategory=subcategory,
			difficulty=difficulty,
			num_questions=num_questions,
			created_by=request.user,
		)

		# If we have items, auto-create a quiz and import questions so the user can start immediately
		items = (result.get('parsed') or {}).get('items') or []
		if items:
			title_part = subcategory.name if subcategory else category.name
			quiz = Quiz(
				title=f"{title_part} - {difficulty.title()} (AI)",
				description=f"Auto-generated quiz for {category.name}{' / ' + subcategory.name if subcategory else ''}",
				category=category,
				subcategory=subcategory,
				difficulty=difficulty,
				is_published=False,  # publish after questions are imported
				status=Quiz.STATUS_DRAFT,
			)
			quiz.save()
			draft.target_quiz = quiz
			draft.save(update_fields=['target_quiz'])

			created_qs = draft.to_questions(quiz)
			if created_qs:
				# Now that we have questions, activate and publish
				quiz.status = Quiz.STATUS_ACTIVE
				quiz.is_published = True
				quiz.save(update_fields=['status', 'is_published'])
				draft.approved = True
				draft.rejected = False
				draft.save(update_fields=['approved', 'rejected'])
				messages.success(request, 'AI quiz is ready. Starting now!')
				return redirect('quiz_session', quiz_id=quiz.id)
		# Fallback: guide user to Admin if no items parsed
		messages.success(request, 'AI draft created. Review and import it via the Admin (AI Question Drafts).')
	except Exception as exc:
		AIQuestionDraft.objects.create(
			provider=(result.get('provider') if 'result' in locals() else 'openai'),
			prompt=(result.get('prompt') if 'result' in locals() else ''),
			raw_response=(result.get('raw') if 'result' in locals() else ''),
			parsed=(result.get('parsed') if 'result' in locals() else {}),
			category=category,
			subcategory=subcategory,
			difficulty=difficulty,
			num_questions=num_questions,
			created_by=request.user,
			error=str(exc),
		)
		messages.error(request, 'Failed to generate questions via AI. A draft with error details was saved for troubleshooting.')

	return redirect('quiz_list')


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
@ensure_csrf_cookie
def quiz_result(request, attempt_id: int):
	attempt = get_object_or_404(Attempt.objects.select_related('quiz', 'user'), pk=attempt_id, user=request.user)
	answers = attempt.answers.select_related('question', 'selected_choice').all()
	# Compute correct count for display (score is stored as percent)
	correct_count = answers.filter(is_correct_cached=True).count()
	# Format time taken (fallback to completed_at - started_at if missing)
	secs = attempt.time_taken
	if secs is None and attempt.started_at and attempt.completed_at:
		secs = int((attempt.completed_at - attempt.started_at).total_seconds())
	if secs is None:
		secs = 0
	m, s = divmod(int(secs), 60)
	time_taken_display = f"{m:02d}:{s:02d}"
	return render(request, 'quizez/quiz_result.html', {
		'attempt': attempt,
		'answers': answers,
		'correct_count': correct_count,
		'time_taken_display': time_taken_display,
	})


@login_required
def answer_explanation(request, answer_id: int):
	"""Fetch or generate an explanation for a specific answer.

	GET: returns {explanation, resources, helpful, not_helpful}
	POST: expects {action: 'helpful'|'not_helpful'} to update feedback counters
	"""
	answer = get_object_or_404(Answer.objects.select_related('attempt', 'question', 'selected_choice'),
							   pk=answer_id, attempt__user=request.user)
	if request.method == 'GET':
		exp = Explanation.objects.filter(question=answer.question).order_by('-created_at').first()
		if not exp:
			q_text = answer.question.text
			correct = answer.question.correct_choice.text if answer.question.correct_choice else ''
			user_sel = answer.selected_choice.text if answer.selected_choice else None
			try:
				data = generate_explanation(q_text, correct, user_sel)
			except Exception as exc:
				return JsonResponse({
					'ok': False,
					'error': str(exc),
				}, status=500)
			exp = Explanation.objects.create(
				question=answer.question,
				summary=data.get('explanation') or '',
				resources=data.get('resources') or [],
				provider=data.get('provider') or '',
			)
		# Link the answer to the explanation for quick access later
		if answer.explanation_id != exp.id:
			answer.explanation = exp
			answer.save(update_fields=['explanation'])
		return JsonResponse({
			'ok': True,
			'explanation': exp.summary,
			'resources': exp.resources,
			'helpful': exp.helpful,
			'not_helpful': exp.not_helpful,
		})
	elif request.method == 'POST':
		action = request.POST.get('action')
		exp = answer.explanation or Explanation.objects.filter(question=answer.question).order_by('-created_at').first()
		if not exp:
			return JsonResponse({'ok': False, 'error': 'No explanation available to rate.'}, status=400)
		if action == 'helpful':
			exp.helpful = (exp.helpful or 0) + 1
			exp.save(update_fields=['helpful'])
		elif action == 'not_helpful':
			exp.not_helpful = (exp.not_helpful or 0) + 1
			exp.save(update_fields=['not_helpful'])
		else:
			return JsonResponse({'ok': False, 'error': 'Invalid action'}, status=400)
		return JsonResponse({'ok': True, 'helpful': exp.helpful, 'not_helpful': exp.not_helpful})
	else:
		return HttpResponseNotAllowed(['GET', 'POST'])

# Create your views here.


@login_required
def quiz_session(request, quiz_id: int):
	"""Single-question session flow with Previous/Next navigation.

	Part 1 focuses on displaying one question at a time, tracking selection,
	and navigating without final submission.
	"""
	quiz = get_object_or_404(Quiz, pk=quiz_id, is_published=True)
	questions = list(quiz.questions.prefetch_related('choices').all())
	total = len(questions)
	if total == 0:
		messages.error(request, 'This quiz has no questions yet.')
		return redirect('quiz_list')

	# Get or create an in-progress attempt for this user
	attempt = Attempt.objects.filter(user=request.user, quiz=quiz, is_completed=False).order_by('-started_at').first()
	if not attempt:
		attempt = Attempt.objects.create(user=request.user, quiz=quiz, total=total)

	if attempt.is_completed:
		return redirect('quiz_result', attempt_id=attempt.id)

	# Enforce time limit (server-side guard)
	# Dynamic time limit by question count: 5→5m, 10→10m, 15→12m, 20→15m; fallback to quiz.time_limit
	minutes_map = {5: 5, 10: 10, 15: 12, 20: 15}
	minutes = minutes_map.get(total, int(getattr(quiz, 'time_limit', 30)))
	time_limit_seconds = max(1, int(minutes) * 60)
	deadline = attempt.started_at + timezone.timedelta(seconds=time_limit_seconds)
	now = timezone.now()
	if now >= deadline:
		# Time up – finalize immediately
		answers = attempt.answers.select_related('question', 'selected_choice').all()
		correct = sum(1 for a in answers if a.is_correct())
		percent = int(round((correct / total) * 100)) if total else 0
		attempt.score = percent
		attempt.total = total
		attempt.is_completed = True
		attempt.time_taken = time_limit_seconds
		attempt.save(update_fields=['score', 'total', 'is_completed', 'time_taken'])
		messages.info(request, 'Time is up. Your quiz was submitted automatically.')
		return redirect('quiz_result', attempt_id=attempt.id)

	# Determine current index (0-based)
	try:
		idx = int(request.GET.get('q', attempt.current_index or 0))
	except Exception:
		idx = attempt.current_index or 0
	idx = max(0, min(idx, total - 1))

	current_q = questions[idx]

	# Track answered questions for review panel/progress
	answered_qids = set(attempt.answers.values_list('question_id', flat=True))
	answered_count = len(answered_qids)

	if request.method == 'POST':
		nav = request.POST.get('nav', 'next')  # 'prev' | 'next' | 'submit'
		choice_id = request.POST.get('choice')

		# Save or update answer selection for current question
		if choice_id:
			try:
				selected = current_q.choices.get(id=int(choice_id))
			except (ValueError, Choice.DoesNotExist):
				selected = None
			ans, _ = Answer.objects.get_or_create(attempt=attempt, question=current_q)
			ans.selected_choice = selected
			ans.save()

		# If user pressed submit on last question, finalize the attempt
		if nav == 'submit' or (nav == 'next' and idx == total - 1):
			# Recalculate correctness and set percent score
			answers = attempt.answers.select_related('question', 'selected_choice').all()
			correct = sum(1 for a in answers if a.is_correct())
			percent = int(round((correct / total) * 100)) if total else 0
			attempt.score = percent
			attempt.total = total
			attempt.is_completed = True
			# Compute time taken from start
			attempt.time_taken = int((timezone.now() - attempt.started_at).total_seconds())
			attempt.save(update_fields=['score', 'total', 'is_completed', 'time_taken'])
			messages.success(request, f'Quiz submitted! You scored {percent}%')
			# Redirect to result page; profile will reflect stats automatically
			return redirect('quiz_result', attempt_id=attempt.id)

		# Otherwise, move index for prev/next
		if nav == 'prev':
			idx = max(0, idx - 1)
		else:
			idx = min(total - 1, idx + 1)

		attempt.current_index = idx
		attempt.total = total
		attempt.save(update_fields=['current_index', 'total'])

		# Redirect to avoid re-posting
		return redirect(f"{request.path}?q={idx}")

	# Preselect previously chosen option, if any
	existing = attempt.answers.filter(question=current_q).first()
	selected_id = existing.selected_choice_id if existing and existing.selected_choice_id else None

	context = {
		'quiz': quiz,
		'question': current_q,
		'total': total,
		'index': idx,  # 0-based
		'counter': idx + 1,  # 1-based for display
		'selected_id': selected_id,
		'has_prev': idx > 0,
		'has_next': idx < total - 1,
		'attempt': attempt,
		# Progress based on answered questions
		'answered_count': answered_count,
		'progress_percent': int((answered_count / total) * 100) if total else 0,
		# Review panel map (index starting at 1 for display)
		'review_map': [
			{
				'n': i + 1,
				'answered': questions[i].id in answered_qids,
				'is_current': i == idx,
			}
			for i in range(total)
		],
		# Timer values – use absolute deadline so refresh is safe
		'deadline_epoch': int(deadline.timestamp()),
		'time_limit_seconds': time_limit_seconds,
	}
	return render(request, 'quizez/quiz_session.html', context)
