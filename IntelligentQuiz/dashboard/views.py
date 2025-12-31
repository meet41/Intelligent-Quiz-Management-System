from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count, Avg, Sum, F
from django.shortcuts import render
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.models import User
from Quizez.models import Quiz, Category, Attempt


def home(request):
	quizzes = Quiz.objects.filter(is_published=True).order_by('-created_at')[:6]
	categories = Category.objects.all()[:8]

	# Build category stats (show first 3 categories in breakdown)
	category_stats = []
	selected = list(categories[:3])  # Top 3 categories for dashboard
	if request.user.is_authenticated and selected:
		# Simple gradient palette
		gradients = [
			'linear-gradient(135deg,#6366f1,#8b5cf6)',
			'linear-gradient(135deg,#22c55e,#059669)',
			'linear-gradient(135deg,#06b6d4,#0284c7)',
			'linear-gradient(135deg,#f59e0b,#d97706)',
		]
		emoji_map = {
			'academic': '📚',
			'entertainment': '🎬',
			'general': '🌐',
			'general knowledge': '🧠',
			'science': '🔬',
			'science & technology': '💻',
			'technology': '💻',
			'history': '📖',
			'math': '➗',
			'sports': '⚽',
			'programming': '👨‍💻',
		}
		for idx, cat in enumerate(selected):
			# Get all completed attempts for this category
			completed = (
				Attempt.objects
				.select_related('quiz')
				.filter(user=request.user, is_completed=True, quiz__category=cat)
				.order_by('-completed_at')
			)
			
			if completed.exists():
				# Calculate average score per attempt
				total_score = 0
				total_possible = 0
				best_score = 0
				total_time = 0
				
				for attempt in completed:
					if attempt.total > 0:
						total_score += attempt.score
						total_possible += attempt.total
						# Track best individual score
						if attempt.score > best_score:
							best_score = attempt.score
						if attempt.time_taken:
							total_time += attempt.time_taken
				
				# Calculate average score per quiz
				count = completed.count()
				avg_score = round(total_score / count, 1) if count > 0 else 0
				avg_total = round(total_possible / count, 1) if count > 0 else 0
				
				# Get last 5 attempts for trend
				recent = list(completed[:5])
				recent_scores = []
				for r in recent:
					if r.total > 0:
						recent_scores.append(int((r.score / r.total) * 100))
				
				# Format time spent
				if total_time >= 3600:
					hours = total_time // 3600
					mins = (total_time % 3600) // 60
					time_display = f"{hours}h {mins}m"
				elif total_time >= 60:
					mins = total_time // 60
					secs = total_time % 60
					time_display = f"{mins}m {secs}s"
				else:
					time_display = f"{total_time}s"
				
				category_stats.append({
					'id': cat.id,
					'name': cat.name,
					'slug': cat.slug,
					'avg_score': avg_score,
					'avg_total': avg_total,
					'best_score': best_score,
					'gradient': gradients[idx % len(gradients)],
					'emoji': emoji_map.get(cat.slug.lower(), '📘'),
					'count': count,
					'time_spent': time_display,
					'recent_scores': recent_scores,
				})
			else:
				# No attempts yet for this category
				category_stats.append({
					'id': cat.id,
					'name': cat.name,
					'slug': cat.slug,
					'avg_score': 0,
					'avg_total': 0,
					'best_score': 0,
					'gradient': gradients[idx % len(gradients)],
					'emoji': emoji_map.get(cat.slug.lower(), '📘'),
					'count': 0,
					'time_spent': '0s',
					'recent_scores': [],
				})
	else:
		# Fallback empty or zero values if unauthenticated
		gradients = [
			'linear-gradient(135deg,#6366f1,#8b5cf6)',
			'linear-gradient(135deg,#22c55e,#059669)',
			'linear-gradient(135deg,#06b6d4,#0284c7)',
			'linear-gradient(135deg,#f59e0b,#d97706)',
		]
		emoji_map = {
			'academic': '📚',
			'entertainment': '🎬',
			'general': '🌐',
			'general knowledge': '🧠',
			'science': '🔬',
			'science & technology': '💻',
			'technology': '💻',
			'history': '📖',
			'math': '➗',
			'sports': '⚽',
			'programming': '👨‍💻',
		}
		for idx, cat in enumerate(selected):
			category_stats.append({
				'id': cat.id,
				'name': cat.name,
				'slug': cat.slug,
				'percent': 0,
				'best_score': 0,
				'gradient': gradients[idx % len(gradients)],
				'emoji': emoji_map.get(cat.slug.lower(), '📘'),
				'count': 0,
				'time_spent': '0s',
				'recent_scores': [],
			})

	context = {
		'quizzes': quizzes,
		'categories': categories,
		'category_stats': category_stats,
	}
	return render(request, 'dashboard/home.html', context)

# Create your views here.


@login_required
def quiz_history(request):
	"""User dashboard: show completed and ongoing quiz attempts with filters/sorting/search."""
	user = request.user
	q = (request.GET.get('q') or '').strip()
	category_id = request.GET.get('category') or ''
	status = request.GET.get('status') or ''  # 'completed' | 'ongoing' | ''(both)
	sort = request.GET.get('sort') or '-date'  # '-date' | 'date' | '-score' | 'score' | '-time' | 'time'

	attempts = Attempt.objects.select_related('quiz__category').filter(user=user)

	# Search by quiz title
	if q:
		attempts = attempts.filter(Q(quiz__title__icontains=q) | Q(quiz__subcategory__name__icontains=q) | Q(quiz__category__name__icontains=q))

	# Filter by category
	if category_id:
		try:
			attempts = attempts.filter(quiz__category_id=int(category_id))
		except Exception:
			pass

	# Filter by completion status
	if status == 'completed':
		attempts = attempts.filter(is_completed=True)
	elif status == 'ongoing':
		attempts = attempts.filter(is_completed=False)

	# Sorting
	sort_map = {
		'date': 'started_at',
		'-date': '-started_at',
		'score': 'score',
		'-score': '-score',
		'time': 'time_taken',
		'-time': '-time_taken',
	}
	attempts = attempts.order_by(sort_map.get(sort, '-started_at'))

	# Split for UI blocks
	ongoing = attempts.filter(is_completed=False)
	completed = attempts.filter(is_completed=True)

	# Categories for filter dropdown
	categories = Category.objects.all().order_by('name')

	# Peer counts: how many other users (excluding current user) are ongoing/completed per quiz
	quiz_ids = list(attempts.values_list('quiz_id', flat=True).distinct())
	base_peers = Attempt.objects.filter(quiz_id__in=quiz_ids, user__isnull=False).exclude(user=user)
	peers_ongoing = {r['quiz_id']: r['cnt'] for r in base_peers.filter(is_completed=False).values('quiz_id').annotate(cnt=Count('user', distinct=True))}
	peers_completed = {r['quiz_id']: r['cnt'] for r in base_peers.filter(is_completed=True).values('quiz_id').annotate(cnt=Count('user', distinct=True))}

	# Helper: compute human time for each attempt (fallback to diff)
	def time_info(a: Attempt):
		secs = a.time_taken
		if secs is None and a.started_at and a.completed_at:
			secs = int((a.completed_at - a.started_at).total_seconds())
		if not secs:
			return 0, '—'
		m, s = divmod(int(secs), 60)
		return int(secs), f"{m:02d}:{s:02d}"

	enriched = []
	for a in attempts:
		secs, tdisp = time_info(a)
		enriched.append({
			'obj': a,
			'category': getattr(a.quiz.category, 'name', '—'),
			'title': a.quiz.title,
			'date': a.started_at,
			'score': a.score,
			'total': a.total,
			'percent': a.score,  # score is already stored as percent in session flow
			'time': tdisp,
			'time_secs': secs,
			'peers_ongoing': peers_ongoing.get(a.quiz_id, 0),
			'peers_completed': peers_completed.get(a.quiz_id, 0),
		})

	# Enriched ongoing items with peer counts for template ease
	ongoing_items = [
		{
			'obj': a,
			'peers_ongoing': peers_ongoing.get(a.quiz_id, 0),
			'peers_completed': peers_completed.get(a.quiz_id, 0),
		}
		for a in ongoing
	]

	context = {
		'attempts_all': enriched,
		'ongoing': ongoing,
		'ongoing_items': ongoing_items,
		'completed': completed,
		'categories': categories,
		'filters': {
			'q': q,
			'category': category_id,
			'status': status,
			'sort': sort,
		},
		'peer_ongoing_by_quiz': peers_ongoing,
		'peer_completed_by_quiz': peers_completed,
	}
	return render(request, 'dashboard/quiz_history.html', context)


@login_required
def dashboard_stats(request):
	"""Statistics and analytics for the current user."""
	user = request.user
	all_attempts = Attempt.objects.select_related('quiz__category').filter(user=user)
	completed_qs = all_attempts.filter(is_completed=True).order_by('-started_at')

	# Totals
	total_attempts = completed_qs.count()
	avg_score = int(round(completed_qs.aggregate(v=Avg('score'))['v'] or 0))

	# Time spent (sum of time_taken, fallback to duration)
	total_secs = 0
	for a in completed_qs:
		secs = a.time_taken
		if secs is None and a.started_at and a.completed_at:
			secs = int((a.completed_at - a.started_at).total_seconds())
		if secs:
			total_secs += int(secs)

	def fmt_hms(secs:int) -> str:
		h = secs // 3600
		m = (secs % 3600) // 60
		s = secs % 60
		if h:
			return f"{h:d}h {m:02d}m"
		return f"{m:d}m {s:02d}s"

	time_spent_display = fmt_hms(total_secs)

	# Category breakdown (completed only)
	cat_rows = (
		completed_qs
		.exclude(quiz__category__isnull=True)
		.values('quiz__category__name')
		.annotate(count=Count('id'), avg=Avg('score'))
		.order_by('-count')
	)
	categories_data = [
		{
			'label': r['quiz__category__name'],
			'count': int(r['count'] or 0),
			'avg': int(round(r['avg'] or 0)),
		}
		for r in cat_rows
	]

	# Progress over time (last 12 attempts)
	last_attempts = list(completed_qs.order_by('started_at')[:12])
	line_labels = [a.started_at.strftime('%b %d') if a.started_at else '' for a in last_attempts]
	line_scores = [int(a.score or 0) for a in last_attempts]

	# Achievements
	achievements = []
	if total_attempts >= 1:
		achievements.append({'title': 'First Quiz Completed', 'desc': 'You completed your first quiz', 'type': 'milestone'})
	if total_attempts >= 10:
		achievements.append({'title': '10 Quizzes Completed', 'desc': 'Great consistency over time', 'type': 'milestone'})
	if any((a.score or 0) >= 100 for a in completed_qs[:50]):
		achievements.append({'title': 'Perfect Score', 'desc': 'Scored 100% on a quiz', 'type': 'skill'})
	if len({getattr(a.quiz.category, 'name', None) for a in completed_qs if getattr(a.quiz, 'category', None)}) >= 3:
		achievements.append({'title': 'Quiz Explorer', 'desc': 'Tried 3+ categories', 'type': 'explore'})

	# Recent activity (attempts both ongoing and completed, last 6)
	recent = all_attempts.order_by('-started_at')[:6]

	# Best/Needs Improvement (completed only)
	best = list(completed_qs.order_by('-score', '-started_at')[:3])
	needs = list(completed_qs.order_by('score', '-started_at')[:3])

	context = {
		'stats': {
			'total_attempts': total_attempts,
			'avg_score': avg_score,
			'time_spent': time_spent_display,
			'time_spent_secs': total_secs,
		},
		'categories_data': categories_data,
		'line_labels': line_labels,
		'line_scores': line_scores,
		'achievements': achievements,
		'recent': recent,
		'best': best,
		'needs': needs,
	}
	return render(request, 'dashboard/stats.html', context)


def leaderboard(request):
	"""Leaderboard view with time-based filtering"""
	filter_type = request.GET.get('filter', 'all_time')
	now = timezone.now()
	
	# Determine date filter
	if filter_type == 'this_week':
		start_date = now - timedelta(days=now.weekday())
		start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
		period_label = 'This Week'
	elif filter_type == 'this_month':
		start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
		period_label = 'This Month'
	else:  # all_time
		start_date = None
		period_label = 'All Time'
	
	# Get all users with completed attempts
	users_data = []
	users = User.objects.filter(
		quiz_attempts__is_completed=True,
		quiz_attempts__user__isnull=False
	).distinct()
	
	print(f"DEBUG: Found {users.count()} users with completed attempts")
	
	for user in users:
		# Get user's completed attempts in the period
		attempts = Attempt.objects.filter(
			user=user,
			is_completed=True
		)
		
		if start_date:
			attempts = attempts.filter(completed_at__gte=start_date)
		
		print(f"DEBUG: User {user.username} has {attempts.count()} attempts")
		
		if attempts.exists():
			total_score = 0
			total_possible = 0
			total_quizzes = attempts.count()
			total_time = 0
			perfect_scores = 0
			
			for attempt in attempts:
				total_score += attempt.score
				total_possible += attempt.total
				if attempt.time_taken:
					total_time += attempt.time_taken
				if attempt.total > 0 and attempt.score == attempt.total:
					perfect_scores += 1
			
			# Calculate metrics
			avg_score = round(total_score / total_quizzes, 1) if total_quizzes > 0 else 0
			accuracy = round((total_score / total_possible) * 100, 1) if total_possible > 0 else 0
			
			# Format time
			if total_time >= 3600:
				hours = total_time // 3600
				mins = (total_time % 3600) // 60
				time_display = f"{hours}h {mins}m"
			elif total_time >= 60:
				mins = total_time // 60
				time_display = f"{mins}m"
			else:
				time_display = f"{total_time}s"
			
			users_data.append({
				'user': user,
				'total_score': total_score,
				'total_quizzes': total_quizzes,
				'avg_score': avg_score,
				'accuracy': accuracy,
				'time_spent': time_display,
				'time_secs': total_time,
				'perfect_scores': perfect_scores,
			})
	
	# Sort by total score , then by accuracy
	users_data.sort(key=lambda x: (x['total_score'], x['accuracy']), reverse=True)
	
	print(f"DEBUG: Total users_data entries: {len(users_data)}")
	for ud in users_data:
		print(f"  - {ud['user'].username}: {ud['total_score']} pts, {ud['accuracy']}%")
	
	# Add rank
	for idx, user_data in enumerate(users_data, 1):
		user_data['rank'] = idx
		# Assign medal
		if idx == 1:
			user_data['medal'] = '🥇'
			user_data['medal_class'] = 'gold'
		elif idx == 2:
			user_data['medal'] = '🥈'
			user_data['medal_class'] = 'silver'
		elif idx == 3:
			user_data['medal'] = '🥉'
			user_data['medal_class'] = 'bronze'
		else:
			user_data['medal'] = None
			user_data['medal_class'] = ''
	
	# Get current user's rank if authenticated
	current_user_data = None
	if request.user.is_authenticated:
		for user_data in users_data:
			if user_data['user'].id == request.user.id:
				current_user_data = user_data
				break
	
	context = {
		'users_data': users_data[:50],  # Top 50
		'filter_type': filter_type,
		'period_label': period_label,
		'current_user_data': current_user_data,
		'total_participants': len(users_data),
	}
	
	return render(request, 'dashboard/leaderboard.html', context)
