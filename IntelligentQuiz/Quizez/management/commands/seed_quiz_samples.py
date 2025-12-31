from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify
from Quizez.models import Category, Subcategory, Quiz, Question, Choice, Attempt, Answer


class Command(BaseCommand):
    help = "Seed sample categories, subcategories, quizzes, questions, choices, and one demo attempt."

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("Seeding sample quiz data..."))

        # Categories
        programming, _ = Category.objects.get_or_create(
            name="Programming",
            defaults={
                "slug": slugify("Programming"),
                "description": "Coding, data structures, and software basics",
                "icon": "fas fa-code",
            },
        )
        science, _ = Category.objects.get_or_create(
            name="Science",
            defaults={
                "slug": slugify("Science"),
                "description": "Physics, chemistry, and general science",
                "icon": "fas fa-flask",
            },
        )

        # Subcategories
        py_basics, _ = Subcategory.objects.get_or_create(
            category=programming,
            name="Python Basics",
            defaults={
                "slug": slugify("Python Basics"),
                "description": "Fundamental Python syntax and concepts",
                "icon": "fab fa-python",
            },
        )
        physics_fund, _ = Subcategory.objects.get_or_create(
            category=science,
            name="Physics Fundamentals",
            defaults={
                "slug": slugify("Physics Fundamentals"),
                "description": "Core physics concepts and units",
                "icon": "fas fa-atom",
            },
        )

        # Quiz
        py_quiz, _ = Quiz.objects.get_or_create(
            title="Python Basics Quiz",
            defaults={
                "description": "Test your knowledge of Python fundamentals",
                "category": programming,
                "subcategory": py_basics,
                "difficulty": Quiz.DIFFICULTY_MEDIUM,
                "status": Quiz.STATUS_ACTIVE,
                "is_published": True,
            },
        )

        # Questions + choices
        questions_payload = [
            {
                "text": "What is the output of print(2 + 3)?",
                "choices": [
                    ("5", True),
                    ("23", False),
                    ("6", False),
                    ("Error", False),
                ],
            },
            {
                "text": "Which of the following is a list literal in Python?",
                "choices": [
                    ("[1, 2, 3]", True),
                    ("(1, 2, 3)", False),
                    ("{1, 2, 3}", False),
                    ("\"123\"", False),
                ],
            },
            {
                "text": "Which keyword is used to define a function in Python?",
                "choices": [
                    ("def", True),
                    ("func", False),
                    ("function", False),
                    ("lambda", False),
                ],
            },
            {
                "text": "What data type is returned by input() in Python 3?",
                "choices": [
                    ("str", True),
                    ("int", False),
                    ("bool", False),
                    ("float", False),
                ],
            },
        ]

        created_questions = []
        for idx, q in enumerate(questions_payload, start=1):
            question, _ = Question.objects.get_or_create(
                quiz=py_quiz,
                text=q["text"],
            )
            created_questions.append(question)
            # Ensure choices exist (idempotent)
            for order, (choice_text, is_correct) in enumerate(q["choices"], start=1):
                Choice.objects.get_or_create(
                    question=question,
                    text=choice_text,
                    defaults={
                        "is_correct": is_correct,
                    },
                )

        # Create a demo attempt with a mix of correct and incorrect answers (user can be null)
        attempt, created_attempt = Attempt.objects.get_or_create(
            user=None, quiz=py_quiz, defaults={"total": len(created_questions)}
        )
        if created_attempt:
            # Answer first two correctly, next two incorrectly
            for i, question in enumerate(created_questions, start=1):
                if i <= 2:
                    # correct choice
                    correct_choice = question.choices.filter(is_correct=True).first()
                    Answer.objects.create(
                        attempt=attempt,
                        question=question,
                        selected_choice=correct_choice,
                    )
                else:
                    # choose a wrong choice
                    wrong_choice = question.choices.filter(is_correct=False).first()
                    Answer.objects.create(
                        attempt=attempt,
                        question=question,
                        selected_choice=wrong_choice,
                    )
            # Update attempt totals
            attempt.total = len(created_questions)
            attempt.score = sum(1 for a in attempt.answers.all() if a.is_correct_cached)
            attempt.is_completed = True
            attempt.save()

        self.stdout.write(self.style.SUCCESS("Sample quiz data seeded successfully."))
