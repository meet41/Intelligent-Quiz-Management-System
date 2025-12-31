from django.core.management.base import BaseCommand
from Quizez.services.ai_generation import generate_questions

class Command(BaseCommand):
    help = "Quickly test AI question generation and print summary."

    def add_arguments(self, parser):
        parser.add_argument("topic", nargs="?", default="Science - Physics")
        parser.add_argument("--difficulty", default="easy")
        parser.add_argument("--num", type=int, default=3)
        parser.add_argument("--provider", default=None)

    def handle(self, *args, **opts):
        res = generate_questions(
            topic=opts["topic"],
            difficulty=opts["difficulty"],
            num_questions=opts["num"],
            provider=opts["provider"],
        )
        self.stdout.write(self.style.SUCCESS(f"Provider: {res['provider']}"))
        self.stdout.write(f"Model meta: {res.get('meta')}")
        self.stdout.write(f"Raw len: {len(res['raw'])}")
        items = res['parsed'].get('items', [])
        self.stdout.write(self.style.SUCCESS(f"Parsed items: {len(items)}"))
        if items:
            for i, it in enumerate(items[:2], 1):
                self.stdout.write(f"Q{i}: {it['question'][:80]}...")
