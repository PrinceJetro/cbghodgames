from django.contrib import admin
from .models import Participant, Quiz, Question, Attempt, Answer, Team, TeamMember, Leaderboard, GuestPlayer, DailyEvent

@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ['user', 'level', 'created_at']

@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ['title', 'quiz_type', 'level', 'date', 'is_active']

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['quiz', 'text', 'correct_option']

@admin.register(Attempt)
class AttemptAdmin(admin.ModelAdmin):
    list_display = ['participant', 'quiz', 'score', 'completed']

@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ['attempt', 'question', 'selected_option', 'is_correct']

@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']

@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ['team', 'participant']

@admin.register(Leaderboard)
class LeaderboardAdmin(admin.ModelAdmin):
    list_display = ['participant', 'quiz', 'score', 'rank', 'date']

@admin.register(GuestPlayer)
class GuestPlayerAdmin(admin.ModelAdmin):
    list_display = ['display_name', 'session_key', 'created_at']

@admin.register(DailyEvent)
class DailyEventAdmin(admin.ModelAdmin):
    list_display = ['day_number', 'title', 'emoji', 'event_date', 'quiz']
