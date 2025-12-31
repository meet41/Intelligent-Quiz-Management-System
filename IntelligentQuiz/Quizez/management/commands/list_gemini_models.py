from django.core.management.base import BaseCommand
import os

class Command(BaseCommand):
    help = "List available Gemini models for this API key (generateContent-supported)."

    def handle(self, *args, **options):
        try:
            import google.generativeai as genai  # type: ignore
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f"google-generativeai not installed: {exc}"))
            return

        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            self.stderr.write(self.style.ERROR("Missing GOOGLE_API_KEY/GEMINI_API_KEY"))
            return

        genai.configure(api_key=api_key)
        try:
            models = [
                (m.name, getattr(m, "supported_generation_methods", []))
                for m in genai.list_models()
            ]
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f"Failed to list models: {exc}"))
            return

        any_printed = False
        for name, methods in models:
            if "generateContent" in methods:
                self.stdout.write(f"- {name} (methods: {', '.join(methods)})")
                any_printed = True
        if not any_printed:
            self.stdout.write("No text-capable models found for this key. Check your API key and product access.")
