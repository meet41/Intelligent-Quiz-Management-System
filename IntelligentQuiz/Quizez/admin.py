from django.contrib import admin
from .models import Category, Quiz, Question, Choice, Attempt, Answer


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
	prepopulated_fields = {"slug": ("name",)}
	search_fields = ["name", "slug"]


class ChoiceInline(admin.TabularInline):
	model = Choice
	extra = 2


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
	list_display = ("quiz", "text")
	search_fields = ("text", "quiz__title")
	inlines = [ChoiceInline]


class QuestionInline(admin.TabularInline):
	model = Question
	extra = 1


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
	list_display = ("title", "category", "is_published", "created_at")
	list_filter = ("is_published", "category")
	search_fields = ("title", "description")


@admin.register(Attempt)
class AttemptAdmin(admin.ModelAdmin):
	list_display = ("user", "quiz", "score", "total", "started_at", "completed_at")
	list_filter = ("quiz",)
	search_fields = ("user__username", "quiz__title")


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
	list_display = ("attempt", "question", "selected_choice")
	search_fields = ("question__text",)

