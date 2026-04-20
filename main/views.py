from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login as auth_login
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum
from django.http import JsonResponse
from django.views.decorators.http import require_POST


from .models import (
    Participant, GuestPlayer, Quiz, Question,
    Attempt, Answer, Team, TeamMember, Leaderboard, DailyEvent
)
from .forms import ParticipantForm

import random


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def _calculate_speed_bonus(time_taken, time_limit, max_bonus):
    """
    Award speed bonus proportional to how fast the answer came in.
    Full bonus if answered in ≤20% of time limit.
    Zero bonus if answered in ≥80% of time limit.
    Linear scale in between.
    """
    fast_threshold = time_limit * 0.20
    slow_threshold = time_limit * 0.80
    if time_taken <= fast_threshold:
        return max_bonus
    elif time_taken >= slow_threshold:
        return 0
    ratio = 1 - (time_taken - fast_threshold) / (slow_threshold - fast_threshold)
    return round(ratio * max_bonus)


def _get_or_create_guest(request, display_name):
    """Get or create a GuestPlayer tied to the current session."""
    if not request.session.session_key:
        request.session.create()
    session_key = request.session.session_key
    guest, _ = GuestPlayer.objects.get_or_create(
        session_key=session_key,
        defaults={'display_name': display_name}
    )
    return guest


# ─── PUBLIC PAGES ─────────────────────────────────────────────────────────────

def home(request):
    today = timezone.now().date()
    daily_event = DailyEvent.objects.filter(event_date=today).first()
    context = {
        'daily_event': daily_event,
        'event_name': 'CBG HOD Games 2026: Brain Battle & Daily Quiz Experience',
        'powered_by': 'Tutorial Haven',
    }
    return render(request, 'home.html', context)


def register(request):
    if request.method == 'POST':
        user_form = UserCreationForm(request.POST)
        participant_form = ParticipantForm(request.POST)
        if user_form.is_valid() and participant_form.is_valid():
            user = user_form.save()
            participant = participant_form.save(commit=False)
            participant.user = user
            participant.save()
            auth_login(request, user)
            messages.success(request, 'Registration successful! Good luck in the qualifiers 🎯')
            return redirect('qualifiers')
    else:
        user_form = UserCreationForm()
        participant_form = ParticipantForm()
    return render(request, 'register.html', {
        'user_form': user_form,
        'participant_form': participant_form
    })

def login(request):
    if request.user.is_authenticated:
        return redirect('qualifiers')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            next_url = request.POST.get('next') or request.GET.get('next') or 'qualifiers'
            return redirect(next_url)
    else:
        form = AuthenticationForm()

    return render(request, 'login.html', {
        'form': form,
        'next': request.GET.get('next', '')
    })

# ─── QUALIFIERS ───────────────────────────────────────────────────────────────

def qualifiers(request):
    if not request.user.is_authenticated:
        messages.warning(request, 'You need to register/login to take the qualifier.')
        return redirect('login')
    print(f"User {request.user.username} accessing qualifiers.")

    participant = get_object_or_404(Participant, user=request.user)
    print(f"Participant {participant.user.username} at level {participant.level} accessing qualifiers.")
    print(f"Looking for active qualifier quiz for level")
    quiz = Quiz.objects.filter(
        quiz_type='qualifier',
        level=participant.level,
        is_active=True
    ).first()

    if not quiz:
        return render(request, 'no_quiz.html', {
            'message': f'No active qualifier quiz for {participant.level}L right now. Check back soon!'
        })

    # Already attempted?
    attempt = Attempt.objects.filter(participant=participant, quiz=quiz).first()
    if attempt and attempt.completed:
        return render(request, 'already_attempted.html', {
            'attempt': attempt,
            'quiz': quiz,
        })

    return redirect('take_quiz', quiz_id=quiz.id)


# ─── DAILY LIFE QUIZ ──────────────────────────────────────────────────────────

def daily_quiz(request):
    """
    Anyone can join — no account needed.
    If user is registered, link attempt to their Participant record.
    Otherwise, ask for a display name and use GuestPlayer.
    """
    today = timezone.now().date()
    daily_event = DailyEvent.objects.filter(event_date=today).first()

    if not daily_event or not daily_event.quiz or not daily_event.quiz.is_active:
        return render(request, 'no_quiz.html', {
            'message': "No Daily Life Quiz is open right now. Come back after today's games! 🎮"
        })

    quiz = daily_event.quiz

    # Registered user path
    if request.user.is_authenticated:
        participant = get_object_or_404(Participant, user=request.user)
        if Attempt.objects.filter(participant=participant, quiz=quiz, completed=True).exists():
            return render(request, 'already_attempted.html', {'quiz': quiz})
        return redirect('take_quiz', quiz_id=quiz.id)

    # Guest path — show name entry form
    if request.method == 'POST':
        display_name = request.POST.get('display_name', '').strip()
        if not display_name:
            messages.error(request, 'Please enter your name to continue.')
            return render(request, 'daily_join.html', {'daily_event': daily_event})

        guest = _get_or_create_guest(request, display_name)

        # Check if this session already attempted
        if Attempt.objects.filter(guest=guest, quiz=quiz, completed=True).exists():
            return render(request, 'already_attempted.html', {'quiz': quiz})

        request.session['guest_id'] = guest.id
        return redirect('take_quiz', quiz_id=quiz.id)

    return render(request, 'daily_join.html', {'daily_event': daily_event})


# ─── TAKE QUIZ ────────────────────────────────────────────────────────────────

def take_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id, is_active=True)

    # Resolve who is playing
    participant = None
    guest = None

    if request.user.is_authenticated:
        participant = get_object_or_404(Participant, user=request.user)
        if Attempt.objects.filter(participant=participant, quiz=quiz, completed=True).exists():
            return render(request, 'already_attempted.html', {'quiz': quiz})
    else:
        guest_id = request.session.get('guest_id')
        if not guest_id:
            # Not registered, hasn't entered name — send to daily join
            return redirect('daily_quiz')
        guest = get_object_or_404(GuestPlayer, id=guest_id)
        if Attempt.objects.filter(guest=guest, quiz=quiz, completed=True).exists():
            return render(request, 'already_attempted.html', {'quiz': quiz})

    questions = list(quiz.questions.all())
    random.shuffle(questions)
    total_time = quiz.time_limit * len(questions)

    if request.method == 'POST':
        attempt = Attempt.objects.create(
            participant=participant,
            guest=guest,
            quiz=quiz
        )
        score = 0
        speed_bonus_total = 0

        for question in questions:
            selected = request.POST.get(f'question_{question.id}')
            time_taken = int(request.POST.get(f'time_{question.id}', quiz.time_limit))

            if selected:
                is_correct = selected.upper() == question.correct_option.upper()
                bonus = 0

                if is_correct:
                    score += quiz.points_correct
                    if quiz.speed_bonus_enabled:
                        bonus = _calculate_speed_bonus(
                            time_taken, quiz.time_limit, quiz.speed_bonus_max
                        )
                        speed_bonus_total += bonus
                else:
                    score += quiz.points_wrong  # 0 normally, negative in buzzer round

                Answer.objects.create(
                    attempt=attempt,
                    question=question,
                    selected_option=selected,
                    is_correct=is_correct,
                    time_taken=time_taken,
                    speed_bonus=bonus
                )

        attempt.score = score
        attempt.speed_bonus_total = speed_bonus_total
        attempt.completed = True
        attempt.completed_at = timezone.now()
        attempt.save()

        # Update leaderboard
        lb_filter = {'quiz': quiz}
        if participant:
            lb_filter['participant'] = participant
        else:
            lb_filter['guest'] = guest

        Leaderboard.objects.update_or_create(
            **lb_filter,
            defaults={
                'score': score,
                'speed_bonus': speed_bonus_total,
                'date': timezone.now().date(),
            }
        )

        # Recalculate team score if finals
        if quiz.quiz_type == 'final' and participant:
            membership = TeamMember.objects.filter(participant=participant).first()
            if membership:
                membership.team.recalculate_score()

        return redirect('quiz_result', attempt_id=attempt.id)

    return render(request, 'take_quiz.html', {
        'quiz': quiz,
        'questions': questions,
        'total_time': total_time,
        'is_speed_round': quiz.speed_bonus_enabled,
        'is_image_round': quiz.round_type == 'image',
    })


# ─── RESULTS ──────────────────────────────────────────────────────────────────

def quiz_result(request, attempt_id):
    # Allow guest access via session
    if request.user.is_authenticated:
        attempt = get_object_or_404(Attempt, id=attempt_id, participant__user=request.user)
    else:
        guest_id = request.session.get('guest_id')
        attempt = get_object_or_404(Attempt, id=attempt_id, guest_id=guest_id)

    answers = attempt.answers.select_related('question').all()
    total_questions = answers.count()
    correct_count = answers.filter(is_correct=True).count()

    # Ranking context
    quiz = attempt.quiz
    rank = Leaderboard.objects.filter(
        quiz=quiz,
        score__gt=attempt.score
    ).count() + 1

    total_possible = quiz.points_correct * total_questions
    outstanding_threshold = total_possible * 0.8
    great_threshold = total_possible * 0.5

    if attempt.total_score >= outstanding_threshold:
        result_title = 'OUTSTANDING! 🏆'
        result_message = 'You absolutely crushed it. Top-tier performance.'
    elif attempt.total_score >= great_threshold:
        result_title = 'GREAT EFFORT! 💪'
        result_message = 'Solid performance. Keep pushing!'
    else:
        result_title = 'NICE TRY! 🎯'
        result_message = 'Every attempt is a step forward. Keep learning!'

    return render(request, 'quiz_result.html', {
        'attempt': attempt,
        'answers': answers,
        'correct_count': correct_count,
        'total_questions': total_questions,
        'rank': rank,
        'quiz': quiz,
        'result_title': result_title,
        'result_message': result_message,
    })


# ─── LEADERBOARD ──────────────────────────────────────────────────────────────

def leaderboard(request):
    today = timezone.now().date()

    # Daily leaderboard — all players (guest + registered) for today's daily quiz
    daily_event = DailyEvent.objects.filter(event_date=today).first()
    daily_scores = []
    if daily_event and daily_event.quiz:
        daily_scores = Leaderboard.objects.filter(
            quiz=daily_event.quiz
        ).order_by('-score', '-speed_bonus')[:20]

    # Overall leaderboard — registered participants only, across all quizzes
    overall_raw = Leaderboard.objects.filter(
        participant__isnull=False
    ).values('participant').annotate(
        total_score=Sum('score'),
        total_bonus=Sum('speed_bonus')
    ).order_by('-total_score', '-total_bonus')[:20]

    participants = {
        p.id: p for p in Participant.objects.select_related('user').all()
    }
    overall_scores = []
    for i, row in enumerate(overall_raw, start=1):
        p = participants.get(row['participant'])
        if p:
            overall_scores.append({
                'rank': i,
                'participant': p,
                'total_score': row['total_score'] + row['total_bonus'],
            })

    # Qualifier top 5 per level
    qualifier_leaderboards = {}
    for level in ['100', '200', '300', '400']:
        qualifier_leaderboards[f'{level}L'] = Leaderboard.objects.filter(
            quiz__quiz_type='qualifier',
            participant__level=level
        ).order_by('-score', '-speed_bonus')[:5]

    # Team standings
    teams = Team.objects.order_by('-total_score')

    # Past daily winners
    past_events = DailyEvent.objects.filter(event_date__lt=today).order_by('-event_date')[:7]
    past_winners = []
    for event in past_events:
        if event.quiz:
            winner_entry = Leaderboard.objects.filter(quiz=event.quiz).order_by('-score', '-speed_bonus').first()
            if winner_entry:
                past_winners.append({
                    'event': event,
                    'winner': winner_entry.player_name,
                    'score': winner_entry.total_score,
                })

    return render(request, 'leaderboard.html', {
        'daily_scores': daily_scores,
        'daily_event': daily_event,
        'overall_scores': overall_scores,
        'qualifier_leaderboards': qualifier_leaderboards,
        'teams': teams,
        'past_winners': past_winners,
    })


# ─── TEAM FORMATION (ADMIN ONLY) ──────────────────────────────────────────────

def team_formation(request):
    if not request.user.is_staff:
        return redirect('home')

    existing_teams = Team.objects.prefetch_related('members__participant__user').all()

    if request.method == 'POST':
        # Clear existing teams
        Team.objects.all().delete()

        levels = ['100', '200', '300', '400']
        qualifiers_pool = {}

        for level in levels:
            top = Leaderboard.objects.filter(
                quiz__quiz_type='qualifier',
                participant__level=level
            ).order_by('-score', '-speed_bonus').select_related('participant')[:5]
            qualifiers_pool[level] = [entry.participant for entry in top]

        # Verify we have enough per level
        for level, pool in qualifiers_pool.items():
            if len(pool) < 5:
                messages.warning(
                    request,
                    f'Only {len(pool)} qualifier(s) found for {level}L — teams may be unbalanced.'
                )

        # Form 5 teams
        for i in range(1, 6):
            team = Team.objects.create(name=f'Team {i}')
            for level in levels:
                pool = qualifiers_pool[level]
                if pool:
                    member = random.choice(pool)
                    TeamMember.objects.create(team=team, participant=member)
                    pool.remove(member)

        messages.success(request, '✅ 5 teams formed successfully! Ready for the Grand Finals.')
        return redirect('teams')

    return render(request, 'team_formation.html', {
        'existing_teams': existing_teams,
        'qualifier_counts': {
            level: Leaderboard.objects.filter(
                quiz__quiz_type='qualifier',
                participant__level=level
            ).count()
            for level in ['100', '200', '300', '400']
        }
    })


def teams(request):
    all_teams = Team.objects.prefetch_related(
        'members__participant__user'
    ).order_by('-total_score')

    team_data = []
    for team in all_teams:
        members = team.members.select_related('participant__user').all()
        team_data.append({
            'team': team,
            'members': members,
            'member_count': members.count(),
        })

    return render(request, 'teams.html', {'team_data': team_data})


# ─── FINALS ───────────────────────────────────────────────────────────────────

def create_dummy_data(request):
    if not request.user.is_staff:
        messages.error(request, 'This is admin-only.')
        return redirect('home')

    if request.method == 'POST':
        # Clear existing dummy data if needed, but for now, just add
        # Create qualifier quiz if not exists
        qualifier_quiz, created = Quiz.objects.get_or_create(
            title='Dummy Qualifier Quiz',
            quiz_type='qualifier',
            defaults={
                'round_type': 'standard',
                'level': '100',  # dummy
                'is_active': False,
                'time_limit': 30,
                'total_questions': 10,
                'points_correct': 10,
                'points_wrong': 0,
            }
        )

        levels = ['100', '200', '300', '400']
        names = [
            'Alice Johnson', 'Bob Smith', 'Charlie Brown', 'Diana Prince', 'Eve Adams',
            'Frank Miller', 'Grace Lee', 'Henry Wilson', 'Ivy Chen', 'Jack Taylor'
        ]

        for level in levels:
            for i in range(8):  # 8 per level to have extras
                first_name, last_name = random.choice(names).split()
                username = f'{first_name.lower()}_{last_name.lower()}_{level}_{i}'
                user = User.objects.create_user(
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    password='password123'  # dummy password
                )
                participant = Participant.objects.create(
                    user=user,
                    level=level,
                    phone=f'123456789{i}'
                )
                # Create leaderboard entry with random score
                score = random.randint(50, 100)
                speed_bonus = random.randint(0, 10)
                Leaderboard.objects.create(
                    participant=participant,
                    quiz=qualifier_quiz,
                    score=score,
                    speed_bonus=speed_bonus
                )

        messages.success(request, 'Dummy data created successfully!')
        return redirect('leaderboard')

    return render(request, 'create_dummy.html', {})  # You might need to create this template or just redirect


def finals(request):
    if not request.user.is_staff:
        messages.error(request, 'Finals management is admin-only.')
        return redirect('home')

    final_quizzes = Quiz.objects.filter(quiz_type='final').order_by('created_at')
    teams = Team.objects.order_by('-total_score')

    return render(request, 'finals.html', {
        'final_quizzes': final_quizzes,
        'teams': teams,
    })


def take_team_quiz(request, team_id, quiz_id):
    if not request.user.is_authenticated:
        return redirect('login')

    team = get_object_or_404(Team, id=team_id)
    quiz = get_object_or_404(Quiz, id=quiz_id)
    participant = get_object_or_404(Participant, user=request.user)

    if not TeamMember.objects.filter(team=team, participant=participant).exists():
        messages.error(request, "You're not a member of this team.")
        return redirect('home')

    # Redirect to standard take_quiz — it handles everything
    return redirect('take_quiz', quiz_id=quiz.id)


# ─── LIVE LEADERBOARD API (for projector display) ─────────────────────────────

def live_leaderboard_api(request, quiz_id):
    """
    JSON endpoint — poll this every few seconds on the projector/admin screen
    to show live scores during finals.
    """
    quiz = get_object_or_404(Quiz, id=quiz_id)

    if quiz.quiz_type == 'final':
        # Team view
        teams = Team.objects.order_by('-total_score')
        data = [
            {
                'rank': i + 1,
                'name': t.name,
                'score': t.total_score,
                'color': t.color,
            }
            for i, t in enumerate(teams)
        ]
    else:
        entries = Leaderboard.objects.filter(quiz=quiz).order_by('-score', '-speed_bonus')[:20]
        data = [
            {
                'rank': i + 1,
                'name': e.player_name,
                'level': e.player_level,
                'score': e.total_score,
            }
            for i, e in enumerate(entries)
        ]

    return JsonResponse({'leaderboard': data, 'quiz': quiz.title})


# ─── ADMIN: REPUBLISH RANKS ───────────────────────────────────────────────────

@require_POST
def recalculate_ranks(request, quiz_id):
    """Admin utility to fix rank numbers after all submissions are in."""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Forbidden'}, status=403)

    entries = Leaderboard.objects.filter(quiz_id=quiz_id).order_by('-score', '-speed_bonus')
    for i, entry in enumerate(entries, start=1):
        entry.rank = i
        entry.save(update_fields=['rank'])

    return JsonResponse({'status': 'ok', 'count': entries.count()})


# ─── LIVE STAGE FOR FINALS ──────────────────────────────────────────────────

def host_dashboard(request, quiz_id):
    if not request.user.is_staff:
        messages.error(request, 'Host dashboard is admin-only.')
        return redirect('home')
    quiz = get_object_or_404(Quiz, id=quiz_id, quiz_type='final')
    return render(request, 'host_dashboard.html', {'quiz': quiz})

def tv_display(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id, quiz_type='final')
    return render(request, 'live_display.html', {'quiz': quiz})

def team_buzzer(request, quiz_id):
    if not request.user.is_authenticated:
        return redirect('login')
    quiz = get_object_or_404(Quiz, id=quiz_id, quiz_type='final')
    participant = get_object_or_404(Participant, user=request.user)
    
    # Verify team membership
    membership = TeamMember.objects.filter(participant=participant).first()
    if not membership:
        messages.error(request, "You are not in any team.")
        return redirect('home')

    return render(request, 'team_buzzer.html', {'quiz': quiz, 'team': membership.team})

@require_POST
def api_host_action(request, quiz_id):
    if not request.user.is_staff:
        return JsonResponse({'error': 'Forbidden'}, status=403)
    quiz = get_object_or_404(Quiz, id=quiz_id)
    action = request.POST.get('action')
    
    if action == 'set_status':
        status = request.POST.get('status')
        if status in dict(Quiz.LIVE_STATUS_CHOICES):
            quiz.live_status = status
            quiz.save(update_fields=['live_status'])
    elif action == 'set_question':
        question_id = request.POST.get('question_id')
        question = get_object_or_404(Question, id=question_id)
        quiz.current_question = question
        quiz.live_status = 'question_active'
        quiz.current_question_start_time = timezone.now()
        quiz.save(update_fields=['current_question', 'live_status', 'current_question_start_time'])
    elif action == 'reset_quiz':
        # Admin utility to clear all attempts for testing
        Attempt.objects.filter(quiz=quiz).delete()
        Team.objects.update(total_score=0)
        quiz.live_status = 'waiting'
        quiz.current_question = None
        quiz.save(update_fields=['live_status', 'current_question'])
    return JsonResponse({'status': 'ok'})

def api_live_state(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    state = {
        'status': quiz.live_status,
        'title': quiz.title,
    }
    if quiz.current_question:
        state['question'] = {
            'id': quiz.current_question.id,
            'text': quiz.current_question.text,
            'option_a': quiz.current_question.option_a,
            'option_b': quiz.current_question.option_b,
            'option_c': quiz.current_question.option_c,
            'option_d': quiz.current_question.option_d,
            'image_url': quiz.current_question.image.url if quiz.current_question.image else None,
            'start_time': quiz.current_question_start_time.isoformat() if quiz.current_question_start_time else None
        }
        if quiz.live_status == 'answer_revealed':
            state['question']['correct_option'] = quiz.current_question.correct_option
            state['question']['explanation'] = quiz.current_question.explanation
            
            # Find who won this question
            winning_answer = Answer.objects.filter(
                question=quiz.current_question, 
                is_correct=True
            ).order_by('id').first()
            
            if winning_answer and winning_answer.attempt.participant:
                membership = TeamMember.objects.filter(participant=winning_answer.attempt.participant).first()
                if membership:
                    state['winning_team_name'] = membership.team.name
    return JsonResponse(state)

@require_POST
def api_submit_buzzer(request, quiz_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    
    quiz = get_object_or_404(Quiz, id=quiz_id)
    participant = get_object_or_404(Participant, user=request.user)
    
    if quiz.live_status != 'question_active' or not quiz.current_question:
        return JsonResponse({'error': 'Question is not active'}, status=400)
        
    # Check 15-second timer
    if quiz.current_question_start_time:
        elapsed = (timezone.now() - quiz.current_question_start_time).total_seconds()
        if elapsed > 15:
            return JsonResponse({'error': 'Time is up!'}, status=400)
            
    selected = request.POST.get('selected_option')
    time_taken = int(request.POST.get('time_taken', quiz.time_limit))
    
    if not selected:
        return JsonResponse({'error': 'No option selected'}, status=400)
        
    # Get or create attempt for the team/participant.
    attempt, created = Attempt.objects.get_or_create(
        participant=participant,
        quiz=quiz
    )
    
    # Check if they already answered THIS question
    if Answer.objects.filter(attempt=attempt, question=quiz.current_question).exists():
        return JsonResponse({'error': 'Already answered'}, status=400)
        
    is_correct = selected.upper() == quiz.current_question.correct_option.upper()
    bonus = 0
    
    if is_correct:
        # Check if another team already got it right
        someone_already_correct = Answer.objects.filter(
            question=quiz.current_question, 
            is_correct=True
        ).exists()
        
        if not someone_already_correct:
            # First team to get it correct!
            attempt.score += quiz.points_correct
            if quiz.speed_bonus_enabled:
                bonus = _calculate_speed_bonus(time_taken, quiz.time_limit, quiz.speed_bonus_max)
                attempt.speed_bonus_total += bonus
                
            # Create the answer record
            Answer.objects.create(
                attempt=attempt,
                question=quiz.current_question,
                selected_option=selected,
                is_correct=True,
                time_taken=time_taken,
                speed_bonus=bonus
            )
            attempt.save()
            
            # Recalculate team score immediately
            membership = TeamMember.objects.filter(participant=participant).first()
            if membership:
                membership.team.recalculate_score()
                
            # Automatically reveal the answer and declare winner
            quiz.live_status = 'answer_revealed'
            quiz.save(update_fields=['live_status'])
            
            return JsonResponse({'status': 'ok'})
        else:
            # Someone else got it first. They are correct but too late.
            is_correct = False # We mark it as false so they don't get points
            # Still record that they answered
            Answer.objects.create(
                attempt=attempt,
                question=quiz.current_question,
                selected_option=selected,
                is_correct=False,
                time_taken=time_taken,
                speed_bonus=0
            )
            return JsonResponse({'status': 'ok'})
    else:
        # Incorrect answer
        attempt.score += quiz.points_wrong
        Answer.objects.create(
            attempt=attempt,
            question=quiz.current_question,
            selected_option=selected,
            is_correct=False,
            time_taken=time_taken,
            speed_bonus=0
        )
        attempt.save()
        return JsonResponse({'status': 'ok'})


# import json
# from datetime import datetime

# # Load the JSON file
# with open('quizzes_data.json', 'r') as file:
#     data = json.load(file)

# # Create quizzes and questions
# for quiz_data in data['quizzes']:
#     # Handle date field
#     if quiz_data['date']:
#         quiz_data['date'] = datetime.strptime(quiz_data['date'], '%Y-%m-%d').date()
    
#     # Extract questions data
#     questions_data = quiz_data.pop('questions')
    
#     # Create quiz
#     quiz = Quiz.objects.create(**quiz_data)
    
#     # Create questions for this quiz
#     for q_data in questions_data:
#         Question.objects.create(quiz=quiz, **q_data)
    
#     print(f"Created quiz: {quiz.title} with {quiz.total_questions} questions")

# print("All quizzes and questions loaded successfully!")