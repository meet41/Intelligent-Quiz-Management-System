from django.db import models
from django.db.models import Q
from django.conf import settings
from django.utils.text import slugify
from django.core.exceptions import ValidationError


class Category(models.Model):
	name = models.CharField(max_length=100, unique=True)
	slug = models.SlugField(max_length=120, unique=True, blank=True)
	description = models.TextField(blank=True, help_text="Brief description of the category")
	icon = models.CharField(max_length=50, blank=True, help_text="Icon class name (e.g., 'fas fa-book')")

	class Meta:
		verbose_name_plural = 'Categories'

	def __str__(self) -> str:
		return self.name

	def save(self, *args, **kwargs):
		if not self.slug:
			self.slug = slugify(self.name)
		return super().save(*args, **kwargs)


class Subcategory(models.Model):
	"""A Subcategory groups quizzes under a Category."""
	category = models.ForeignKey(Category, related_name="subcategories", on_delete=models.CASCADE)
	name = models.CharField(max_length=100)
	slug = models.SlugField(max_length=120, blank=True)
	description = models.TextField(blank=True)
	icon = models.CharField(max_length=50, blank=True, help_text="Icon class (e.g., 'fas fa-book')")

	class Meta:
		unique_together = ("category", "slug")
		# Prevent duplicate subcategory names within the same category
		constraints = [
			models.UniqueConstraint(fields=["category", "name"], name="unique_subcategory_name_per_category"),
		]
		verbose_name_plural = "Subcategories"

	def __str__(self) -> str:
		return f"{self.category.name} / {self.name}"

	def save(self, *args, **kwargs):
		if not self.slug:
			self.slug = slugify(self.name)
		return super().save(*args, **kwargs)

	def get_quiz_count(self) -> int:
		"""Return count of active/published quizzes under this subcategory."""
		# Use default reverse relation name if related_name isn't set
		return self.quiz_set.count()


class Quiz(models.Model):
	DIFFICULTY_EASY = "easy"
	DIFFICULTY_MEDIUM = "medium"
	DIFFICULTY_HARD = "hard"
	DIFFICULTY_CHOICES = [
		(DIFFICULTY_EASY, "Easy"),
		(DIFFICULTY_MEDIUM, "Medium"),
		(DIFFICULTY_HARD, "Hard"),
	]

	STATUS_DRAFT = "draft"
	STATUS_ACTIVE = "active"
	STATUS_ARCHIVED = "archived"
	STATUS_CHOICES = [
		(STATUS_DRAFT, "Draft"),
		(STATUS_ACTIVE, "Active"),
		(STATUS_ARCHIVED, "Archived"),
	]

	title = models.CharField(max_length=200)
	slug = models.SlugField(max_length=220, unique=True, blank=True)
	description = models.TextField(blank=True)
	category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
	subcategory = models.ForeignKey('Subcategory', on_delete=models.SET_NULL, null=True, blank=True)
	difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default=DIFFICULTY_MEDIUM)
	status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_DRAFT)
	is_published = models.BooleanField(default=True)
	# Quiz-level controls
	time_limit = models.PositiveIntegerField(default=30, help_text="Time limit in minutes")
	passing_score = models.PositiveIntegerField(default=60, help_text="Passing score percentage")
	max_attempts = models.PositiveIntegerField(default=3, help_text="Maximum number of attempts allowed per user")
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		verbose_name_plural = 'Quizzes'
		ordering = ['-created_at']
		indexes = [
			models.Index(fields=["status", "is_published"]),
			models.Index(fields=["-created_at"]),
		]

	def __str__(self) -> str:
		return self.title

	def clean(self):
		"""Ensure subcategory belongs to selected category."""
		if self.subcategory:
			# If category not explicitly provided, infer it from subcategory
			if self.category is None:
				self.category = self.subcategory.category
			elif self.subcategory.category_id != self.category_id:
				raise ValidationError({
					"subcategory": "Selected subcategory does not belong to the chosen category."
				})

		# Publishing guard: when activating or publishing, require at least 1 question
		# and each question must have at least one correct choice
		if self.pk and (self.status == self.STATUS_ACTIVE or self.is_published):
			qs = self.questions.all()
			if not qs.exists():
				raise ValidationError({
					"status": "An active/published quiz must contain at least one question.",
				})
			# every question must have a correct choice
			missing_correct = [q.id for q in qs if not q.choices.filter(is_correct=True).exists()]
			if missing_correct:
				raise ValidationError({
					"status": "All questions in an active/published quiz must have a correct choice.",
				})


	def save(self, *args, **kwargs):
		"""Robust unique-slug generation with race-safe retry.

		- Generates a base slug from title (or provided slug)
		- Appends -2, -3, ... if duplicates exist
		- On rare race-condition IntegrityError, appends a short random suffix and retries once
		"""
		# Build base slug
		base_slug = slugify(self.slug or self.title) or "quiz"
		candidate = base_slug
		idx = 1
		# Ensure uniqueness against other rows
		while Quiz.objects.filter(slug=candidate).exclude(pk=self.pk).exists():
			idx += 1
			candidate = f"{base_slug}-{idx}"
		self.slug = candidate

		# Run model-level validations (excluding validate_unique to avoid false positives pre-save)
		self.clean()

		from django.db import IntegrityError
		try:
			return super().save(*args, **kwargs)
		except IntegrityError as ie:
			# Handle extremely rare race where the same slug was inserted between our check and save
			if 'slug' in str(ie).lower():
				import uuid
				self.slug = f"{base_slug}-{uuid.uuid4().hex[:6]}"
				return super().save(*args, **kwargs)
			raise

	@property
	def question_count(self) -> int:
		return self.questions.count()


class Question(models.Model):
	QUESTION_TYPE_MULTIPLE = 'multiple_choice'
	QUESTION_TYPE_TRUE_FALSE = 'true_false'
	QUESTION_TYPE_SHORT = 'short_answer'
	QUESTION_TYPE_CHOICES = [
		(QUESTION_TYPE_MULTIPLE, 'Multiple Choice'),
		(QUESTION_TYPE_TRUE_FALSE, 'True/False'),
		(QUESTION_TYPE_SHORT, 'Short Answer'),
	]

	quiz = models.ForeignKey(Quiz, related_name='questions', on_delete=models.CASCADE)
	text = models.TextField()
	image = models.ImageField(upload_to='questions/', blank=True, null=True)
	question_type = models.CharField(max_length=20, choices=QUESTION_TYPE_CHOICES, default=QUESTION_TYPE_MULTIPLE)
	points = models.PositiveIntegerField(default=1)

	def __str__(self) -> str:
		return f"{self.quiz.title}: {self.text[:50]}"

	@property
	def correct_choice(self):
		"""Return the correct choice for this question if available."""
		return self.choices.filter(is_correct=True).first()


class Choice(models.Model):
	question = models.ForeignKey(Question, related_name='choices', on_delete=models.CASCADE)
	text = models.CharField(max_length=255)
	is_correct = models.BooleanField(default=False)

	def __str__(self) -> str:
		return self.text

	class Meta:
		constraints = [
			# Ensure at most one correct answer per question
			models.UniqueConstraint(
				fields=["question"],
				condition=Q(is_correct=True),
				name="unique_correct_choice_per_question",
			)
		]


class Attempt(models.Model):
	"""UserQuizAttempt: tracks per-user progress on a quiz."""
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='quiz_attempts')
	quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
	score = models.PositiveIntegerField(default=0)
	total = models.PositiveIntegerField(default=0)
	current_index = models.PositiveIntegerField(default=0, help_text="Number of questions answered so far")
	is_completed = models.BooleanField(default=False)
	started_at = models.DateTimeField(auto_now_add=True)
	completed_at = models.DateTimeField(auto_now=True)
	# Total time taken in seconds
	time_taken = models.PositiveIntegerField(null=True, blank=True, help_text="Total time taken in seconds")

	def __str__(self) -> str:
		return f"{self.user or 'Anonymous'} - {self.quiz} ({self.score}/{self.total})"

	def calculate_score(self) -> int:
		"""Calculate raw score from answers' correctness (1 point per correct unless question points is used)."""
		# If question-level points are present, sum those; else default to 1 per correct
		answers = self.answers.select_related('question').all()
		if not answers:
			return 0
		points = 0
		for a in answers:
			if a.is_correct_cached:
				points += getattr(a.question, 'points', 1)
		return points

	def update_progress(self):
		"""Recompute total answered, correct answers, and score."""
		ans = self.answers.all()
		self.current_index = ans.count()
		correct = ans.filter(is_correct_cached=True).count()
		self.score = correct  # raw correct count (kept for backward-compat)
		self.total = self.quiz.questions.count()
		# We keep score as correct count; a consumer may compute weighted with calculate_score()
		self.save(update_fields=['current_index', 'score', 'total'])


class Answer(models.Model):
	attempt = models.ForeignKey(Attempt, related_name='answers', on_delete=models.CASCADE)
	question = models.ForeignKey(Question, on_delete=models.CASCADE)
	selected_choice = models.ForeignKey(Choice, on_delete=models.SET_NULL, null=True)
	is_correct_cached = models.BooleanField(default=False, help_text="Cached correctness for faster queries")
	# Per-question time taken in seconds
	time_taken = models.PositiveIntegerField(null=True, blank=True, help_text="Time taken to answer this question (seconds)")
	# Optional link to an AI-generated explanation (cached and reused across users)
	explanation = models.ForeignKey('Explanation', null=True, blank=True, on_delete=models.SET_NULL, related_name='answers')

	def is_correct(self) -> bool:
		return bool(self.selected_choice and self.selected_choice.is_correct)

	def save(self, *args, **kwargs):
		# Update cached correctness before saving
		self.is_correct_cached = self.is_correct()
		return super().save(*args, **kwargs)

	class Meta:
		constraints = [
			models.UniqueConstraint(fields=["attempt", "question"], name="unique_answer_per_attempt_question"),
		]
		indexes = [
			models.Index(fields=["attempt", "question"]),
		]

    


# Create your models here.


	class Explanation(models.Model):
		"""AI-generated explanation for a question.

		Explanations are generally scoped to a Question (and its correct answer). They can be
		reused across attempts and users. Feedback counts help improve future versions.
		"""

		question = models.ForeignKey(Question, related_name='explanations', on_delete=models.CASCADE)
		summary = models.TextField(blank=True)
		resources = models.JSONField(default=list, help_text="List of {title, url} links")
		provider = models.CharField(max_length=32, blank=True)
		helpful = models.PositiveIntegerField(default=0)
		not_helpful = models.PositiveIntegerField(default=0)
		created_at = models.DateTimeField(auto_now_add=True)
		updated_at = models.DateTimeField(auto_now=True)

		class Meta:
			indexes = [
				models.Index(fields=["question", "-created_at"]),
			]

		def __str__(self) -> str:
			return f"Explanation for Q{self.question_id} (👍{self.helpful}/👎{self.not_helpful})"


class AIQuestionDraft(models.Model):
	"""Cache for AI-generated question drafts before human approval/import.

	The 'parsed' field should contain a normalized structure like:
	{
	  "items": [
	    {
	      "question": "...",
	      "choices": ["A", "B", "C", "D"],
	      "correct_index": 1,
	      "explanation": "optional",
	      "points": 1
	    },
	    ...
	  ]
	}
	"""

	PROVIDER_OPENAI = "openai"
	PROVIDER_ANTHROPIC = "anthropic"
	PROVIDER_GEMINI = "gemini"
	PROVIDER_CHOICES = [
		(PROVIDER_OPENAI, "OpenAI"),
		(PROVIDER_ANTHROPIC, "Anthropic"),
		(PROVIDER_GEMINI, "Gemini"),
	]

	provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES, default=PROVIDER_OPENAI)
	prompt = models.TextField(blank=True)
	raw_response = models.TextField(blank=True)
	parsed = models.JSONField(default=dict)

	# Context/metadata
	category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.SET_NULL)
	subcategory = models.ForeignKey(Subcategory, null=True, blank=True, on_delete=models.SET_NULL)
	difficulty = models.CharField(max_length=10, blank=True)
	num_questions = models.PositiveIntegerField(default=0)
	target_quiz = models.ForeignKey(Quiz, null=True, blank=True, on_delete=models.SET_NULL)
	created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
	created_at = models.DateTimeField(auto_now_add=True)
	approved = models.BooleanField(default=False)
	rejected = models.BooleanField(default=False)
	error = models.TextField(blank=True)

	class Meta:
		ordering = ["-created_at"]

	def __str__(self) -> str:
		label = self.subcategory.name if self.subcategory else (self.category.name if self.category else "Unscoped")
		return f"AI Draft ({self.provider}) - {label} [{self.num_questions}]"

	def to_questions(self, quiz: Quiz) -> list:
		"""Import the parsed items into real Question/Choice rows under the given quiz.

		Returns the list of created Question instances.
		"""
		items = (self.parsed or {}).get("items") or []
		created = []
		for item in items:
			text = item.get("question") or item.get("prompt") or ""
			choices = item.get("choices") or []
			correct_index = item.get("correct_index")
			points = item.get("points") or 1
			if not text or not choices or correct_index is None:
				continue
			# Create question
			q = Question.objects.create(
				quiz=quiz,
				text=text,
				question_type=Question.QUESTION_TYPE_MULTIPLE,
				points=points,
			)
			for idx, ctext in enumerate(choices):
				Choice.objects.create(question=q, text=str(ctext), is_correct=(idx == correct_index))
			created.append(q)
		return created
