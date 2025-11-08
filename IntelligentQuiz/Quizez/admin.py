from django.contrib import admin
from .models import Category, Subcategory, Quiz, Question, Choice, Attempt, Answer, AIQuestionDraft


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
	prepopulated_fields = {"slug": ("name",)}
	search_fields = ["name", "slug"]


@admin.register(Subcategory)
class SubcategoryAdmin(admin.ModelAdmin):
	list_display = ("name", "category", "icon")
	list_filter = ("category",)
	search_fields = ("name", "category__name")
	prepopulated_fields = {"slug": ("name",)}


class ChoiceInline(admin.TabularInline):
	model = Choice
	extra = 2


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
	list_display = ("quiz", "text", "question_type", "points")
	search_fields = ("text", "quiz__title")
	inlines = [ChoiceInline]


class QuestionInline(admin.TabularInline):
	model = Question
	extra = 1


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
	list_display = ("title", "category", "subcategory", "difficulty", "status", "is_published", "time_limit", "passing_score", "max_attempts", "created_at")
	list_filter = ("is_published", "category", "subcategory", "difficulty", "status")
	search_fields = ("title", "description")


@admin.register(Attempt)
class AttemptAdmin(admin.ModelAdmin):
	list_display = ("user", "quiz", "score", "total", "time_taken", "started_at", "completed_at")
	list_filter = ("quiz",)
	search_fields = ("user__username", "quiz__title")


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
	list_display = ("attempt", "question", "selected_choice", "is_correct_cached", "time_taken")
	search_fields = ("question__text",)


@admin.register(AIQuestionDraft)
class AIQuestionDraftAdmin(admin.ModelAdmin):
	list_display = ("provider", "category", "subcategory", "difficulty", "num_questions", "target_quiz", "created_by", "approved", "rejected", "created_at")
	list_filter = ("provider", "approved", "rejected", "difficulty", "created_by")
	search_fields = ("prompt",)
	actions = ["approve_and_import"]

	@admin.action(description="Approve and import into target quiz")
	def approve_and_import(self, request, queryset):
		success = 0
		skipped = 0
		for draft in queryset:
			quiz = draft.target_quiz
			if not quiz:
				skipped += 1
				continue
			try:
				created = draft.to_questions(quiz)
				if created:
					draft.approved = True
					draft.rejected = False
					draft.save(update_fields=["approved", "rejected"])
					success += 1
				else:
					skipped += 1
			except Exception as exc:
				skipped += 1
		self.message_user(request, f"Imported: {success}, Skipped: {skipped}")

