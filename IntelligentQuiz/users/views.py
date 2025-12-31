from django.contrib import messages
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.shortcuts import redirect, render
from .forms import UserUpdateForm, ProfileUpdateForm
from django.views.decorators.csrf import csrf_protect
from django.contrib import messages


@login_required
def logout_view(request):
    if request.method == 'POST':
        logout(request)
        messages.success(request, 'You have been successfully logged out.')
        return redirect('home')
    return render(request, 'users/logout.html')

@csrf_protect
def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            remember_me = request.POST.get('remember_me', False)
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                if not remember_me:
                    # Session expires when browser closes
                    request.session.set_expiry(0)
                else:
                    # Session expires in 30 days
                    request.session.set_expiry(2592000)
                messages.success(request, f'Welcome back, {username}!')
                return redirect('home')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = AuthenticationForm()
    return render(request, 'users/login.html', {'form': form})


def register(request):
	if request.method == 'POST':
		form = UserCreationForm(request.POST)
		if form.is_valid():
			user = form.save()
			login(request, user)
			messages.success(request, 'Registration successful. Welcome!')
			return redirect('home')
	else:
		form = UserCreationForm()
	return render(request, 'users/register.html', {'form': form})


@login_required
def profile(request):
    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)
        
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, 'Your profile has been updated!')
            return redirect('profile')
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=request.user.profile)

    # Get quiz statistics
    quiz_attempts = request.user.quiz_attempts.all()
    total_quizzes = quiz_attempts.count()
    if total_quizzes > 0:
        avg_score = sum(attempt.score for attempt in quiz_attempts) / total_quizzes
        best_score = max(attempt.score for attempt in quiz_attempts)
    else:
        avg_score = 0
        best_score = 0

    context = {
        'u_form': u_form,
        'p_form': p_form,
        'quiz_count': total_quizzes,
        'avg_score': round(avg_score, 1),
        'best_score': best_score,
        'recent_attempts': quiz_attempts.order_by('-completed_at')[:5]
    }
    
    return render(request, 'users/profile.html', context)
