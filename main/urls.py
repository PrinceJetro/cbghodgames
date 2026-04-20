from django.urls import path
from . import views

urlpatterns = [
    # ── Public ──────────────────────────────────────────────────────────────
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', views.login, name='login'),

    # ── Qualifiers (registered users only) ──────────────────────────────────
    path('qualifiers/', views.qualifiers, name='qualifiers'),

    # ── Daily Life Quiz (open to all) ───────────────────────────────────────
    path('daily/', views.daily_quiz, name='daily_quiz'),

    # ── Core Quiz Flow ───────────────────────────────────────────────────────
    path('quiz/<int:quiz_id>/', views.take_quiz, name='take_quiz'),
    path('result/<int:attempt_id>/', views.quiz_result, name='quiz_result'),

    # ── Leaderboard ──────────────────────────────────────────────────────────
    path('leaderboard/', views.leaderboard, name='leaderboard'),

    # ── Teams ────────────────────────────────────────────────────────────────
    path('teams/', views.teams, name='teams'),
    path('team-formation/', views.team_formation, name='team_formation'),  # admin
    path('create-dummy/', views.create_dummy_data, name='create_dummy'),  # admin
    path('team/quiz/<int:quiz_id>/', views.team_buzzer, name='team_buzzer'),

    # ── Finals (admin management view) ───────────────────────────────────────
    path('finals/', views.finals, name='finals'),

    # ── Live / API ────────────────────────────────────────────────────────────
    # Poll this from a projector browser tab every 3–5s during finals
    path('api/leaderboard/<int:quiz_id>/', views.live_leaderboard_api, name='live_leaderboard_api'),
    path('api/recalculate-ranks/<int:quiz_id>/', views.recalculate_ranks, name='recalculate_ranks'),
    
    # ── Live Stage (Finals) ───────────────────────────────────────────────────
    path('host/quiz/<int:quiz_id>/', views.host_dashboard, name='host_dashboard'),
    path('tv/quiz/<int:quiz_id>/', views.tv_display, name='tv_display'),
    path('api/live-state/<int:quiz_id>/', views.api_live_state, name='api_live_state'),
    path('api/host-action/<int:quiz_id>/', views.api_host_action, name='api_host_action'),
    path('api/submit-buzzer/<int:quiz_id>/', views.api_submit_buzzer, name='api_submit_buzzer'),
]