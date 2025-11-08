# IntelligentQuiz (Django)

A simple multi-app Django project for creating and taking quizzes. Includes:
- Quizzes with categories, questions, and choices
- User attempts with scoring and results review
- Authentication: login, logout, register, profile
- Admin for managing quizzes and questions

## Quick start (Windows PowerShell)

1) Open a terminal in the project folder:

```powershell
cd "E:\Infosys SpringBoard Internship\IntelligentQuiz"
```

2) Activate the virtual environment (created at the workspace root):

```powershell
# If your venv is at E:\Infosys SpringBoard Internship\.venv
..\.venv\Scripts\Activate.ps1
```

3) Install dependencies:

```powershell
pip install -r requirements.txt
```

4) Create and apply database migrations:

```powershell
python manage.py makemigrations
python manage.py migrate
```

5) Create a superuser (optional, recommended):

```powershell
python manage.py createsuperuser
```

6) Run the development server:

```powershell
python manage.py runserver
```

Open http://127.0.0.1:8000/ in your browser.

- Home: lists recent quizzes
- Quizzes: all quizzes and take flow
- Login/Register: user flows
- Admin: http://127.0.0.1:8000/admin/

## Notes

- Django: 5.2.7 (matches this project). Pillow 11+ is used for ImageField support on modern Python versions.
- Static files are served via Django during development; see `templates/base.html` for references.
- Media uploads (question images) are stored in `media/` during development. Don’t commit uploaded files to git.

## Data model

- Category(name, slug)
- Quiz(title, description, category, is_published)
- Question(quiz, text, image)
- Choice(question, text, is_correct)
- Attempt(user, quiz, score, total)
- Answer(attempt, question, selected_choice)

## Troubleshooting

- If PowerShell blocks activation, run PowerShell as Administrator once and execute:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

- To log your terminal session:

```powershell
Start-Transcript -Path .\session.log
# ...run your commands...
Stop-Transcript
```

- If `pip install` fails, upgrade build tools and retry:

```powershell
python -m pip install --upgrade pip setuptools wheel
pip install --only-binary=:all: pillow
```

## Project structure (high level)

- `IntelligentQuiz/` – project settings and URLs
- `dashboard/` – home page
- `Quizez/` – quiz models, views, URLs
- `users/` – auth views (login/logout/register/profile)
- `templates/` – base + pages
- `static/` – CSS/JS (dev)
- `media/` – uploaded images (dev)

Enjoy building! 🎯

## AI Question Generation (Task 2.3)

This project includes AI-powered multiple-choice question generation via OpenAI (ChatGPT) or Anthropic (Claude). The flow caches raw AI output as drafts so you can review and import them into real quizzes from the Django Admin.

### 1) Configure environment

Edit `.env` in `IntelligentQuiz/` and set at least one provider key:

```properties
# AI Integration
OPENAI_API_KEY='your-openai-key'
# or
ANTHROPIC_API_KEY='your-anthropic-key'

# Optional overrides (these defaults are used if not set)
# AI_PROVIDER='openai'           # 'openai' or 'anthropic'
# OPENAI_MODEL='gpt-3.5-turbo'
# ANTHROPIC_MODEL='claude-2.1'
```

Restart the server after editing `.env`.

### 2) Generate a draft

From the site UI:
- Go to a Category, select a Subcategory, choose Difficulty and Question count.
- Click Start. The app will call the AI provider and save an `AIQuestionDraft` containing:
	- The exact prompt
	- The raw provider response
	- A normalized JSON payload under `parsed.items`

If the provider returns non-JSON or an error occurs, we still save a draft with `error` text to help you diagnose.

### 3) Review and import in Admin

- Go to `/admin/` → AI Question Drafts.
- Open your draft. Set a `Target quiz` to import into (create a quiz first if needed).
- Back in the Drafts list, select the draft and run the action: “Approve and import into target quiz”.
- The system will create `Question` and `Choice` records under the chosen quiz. Draft is marked approved.

### 4) Take the quiz

- Visit the quiz page and click “Take” to answer the imported questions.
- Submit to see your score and review answers. The result page now uses `{% widthratio %}` to compute percentages.

### Notes and limitations

- Provider selection: If `AI_PROVIDER` isn’t set, the app uses `openai` when `OPENAI_API_KEY` exists; otherwise `anthropic`.
- The service asks for strictly JSON output; if the model returns extra text or code fences, we attempt to extract the JSON blob.
- Normalization accepts alternate field names like `options` and maps letters like `"B"` to `correct_index`.
- Import skips malformed items (missing text/choices/correct_index).
- Everything is cached in `AIQuestionDraft` for transparency and troubleshooting.

# IntelligentQuiz — Setup and Run (Windows PowerShell)

This guide gets you from zero to a working Django quiz app with users, quizzes, questions, and results.

## Prerequisites
- Python 3.11+ (tested with 3.13)
- Windows PowerShell (ExecutionPolicy set to `RemoteSigned`)

Optional (for logging your session):
- Start logging: `Start-Transcript -Path .\setup-log.txt`
- Stop logging: `Stop-Transcript`

## 1) Create and activate a virtual environment
From the project folder containing `.venv` (or create one if you don’t have it):

```powershell
# If you do not have a venv yet:
python -m venv .venv

# Activate (PowerShell)
.\.venv\Scripts\Activate.ps1
```

If you get an execution policy error, run PowerShell as Administrator once and:
```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

## 2) Install dependencies
```powershell
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

Notes:
- This project was generated with Django 5.2.7. The `requirements.txt` pins Django to match.
- Pillow is pinned to a version that ships prebuilt wheels for modern Python versions.

## 3) Apply database migrations
```powershell
python manage.py makemigrations
python manage.py migrate
```

## 4) Create a superuser (to add quizzes via admin)
```powershell
python manage.py createsuperuser
```

## 5) Run the development server
```powershell
python manage.py runserver
```

Visit http://127.0.0.1:8000/ for the site and http://127.0.0.1:8000/admin/ for the admin.

## 6) Add sample data
- Log in to the admin at `/admin/` with your superuser.
- Create one or more Categories.
- Create a Quiz (is_published = true).
- Add Questions to the Quiz and a few Choices per question (mark the correct one with `is_correct`).

Now you can:
- See quizzes on the Home page or the Quizzes page.
- Register/Login, take a quiz, and view your results.
- See your attempt history on your Profile page.

## Project structure highlights
- Apps: `dashboard/`, `Quizez/`, `users/`
- Templates: `templates/` (global), including `base.html`
- Static: `static/` (CSS/JS)
- Media: `media/` for uploaded images (e.g., question images)

## Common issues
- "django-admin not found": Activate your venv first, or ensure Python Scripts directory is on PATH.
- PowerShell activation blocked: set ExecutionPolicy to `RemoteSigned` as shown above.
- Pillow build errors: make sure you’re using a modern Pillow (this repo pins `>=11,<12`). Also upgrade `pip setuptools wheel`.

## How to run tests (optional)
This project doesn’t ship with unit tests yet. You can add them under each app’s `tests.py` and run:
```powershell
python manage.py test
```

## Next steps / ideas
- Add pagination and categories to the quiz list.
- Add per-question explanations and per-attempt review details.
- Add support for multi-select questions.
- Add API endpoints (Django REST Framework) if needed.
