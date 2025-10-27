from django.db import models
from django.conf import settings
from django.utils.text import slugify


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


class Quiz(models.Model):
	title = models.CharField(max_length=200)
	description = models.TextField(blank=True)
	category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
	is_published = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)

	def __str__(self) -> str:
		return self.title

	@property
	def question_count(self) -> int:
		return self.questions.count()


class Question(models.Model):
	quiz = models.ForeignKey(Quiz, related_name='questions', on_delete=models.CASCADE)
	text = models.TextField()
	image = models.ImageField(upload_to='questions/', blank=True, null=True)

	def __str__(self) -> str:
		return f"{self.quiz.title}: {self.text[:50]}"


class Choice(models.Model):
	question = models.ForeignKey(Question, related_name='choices', on_delete=models.CASCADE)
	text = models.CharField(max_length=255)
	is_correct = models.BooleanField(default=False)

	def __str__(self) -> str:
		return self.text


class Attempt(models.Model):
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='quiz_attempts')
	quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
	score = models.PositiveIntegerField(default=0)
	total = models.PositiveIntegerField(default=0)
	started_at = models.DateTimeField(auto_now_add=True)
	completed_at = models.DateTimeField(auto_now=True)

	def __str__(self) -> str:
		return f"{self.user or 'Anonymous'} - {self.quiz} ({self.score}/{self.total})"


class Answer(models.Model):
	attempt = models.ForeignKey(Attempt, related_name='answers', on_delete=models.CASCADE)
	question = models.ForeignKey(Question, on_delete=models.CASCADE)
	selected_choice = models.ForeignKey(Choice, on_delete=models.SET_NULL, null=True)

	def is_correct(self) -> bool:
		return bool(self.selected_choice and self.selected_choice.is_correct)


# Create your models here.
