from django.db import models
from django.utils import timezone


class Participant(models.Model):
    """Registered participants (for qualifiers and finals)."""
    user = models.OneToOneField('auth.User', on_delete=models.CASCADE)
    level = models.CharField(max_length=10, choices=[
        ('100', '100L'),
        ('200', '200L'),
        ('300', '300L'),
        ('400', '400L'),
    ])
    phone = models.CharField(max_length=15, blank=True)  # optional contact
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.level})"


class GuestPlayer(models.Model):
    """
    No-account players for the Daily Life Quiz.
    They just enter a display name — no registration required.
    Tied to session or a simple token for anti-duplicate.
    """
    display_name = models.CharField(max_length=60)
    session_key = models.CharField(max_length=40, unique=True)  # Django session key
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.display_name


class Quiz(models.Model):
    QUIZ_TYPES = [
        ('qualifier', 'Level Qualifier'),
        ('daily', 'Daily Life Quiz'),
        ('final', 'Grand Finals'),
    ]
    ROUND_TYPES = [
        ('general', 'General Biology Round'),
        ('department', 'CBG Department Trivia'),
        ('speed', 'Speed Round'),
        ('image', 'Image / Diagram Identification'),
        ('final_high', 'Final High Stakes Round'),
        ('standard', 'Standard'),   # for qualifiers and daily
    ]

    title = models.CharField(max_length=200)
    quiz_type = models.CharField(max_length=20, choices=QUIZ_TYPES)
    round_type = models.CharField(max_length=20, choices=ROUND_TYPES, default='standard')
    level = models.CharField(max_length=10, blank=True, null=True,
                             help_text="Set only for qualifier quizzes")
    date = models.DateField(blank=True, null=True,
                            help_text="Set for daily quizzes")
    day_label = models.CharField(max_length=100, blank=True,
                                 help_text="E.g. 'Football Day ⚽' — shown on the quiz page")
    is_active = models.BooleanField(default=True)
    time_limit = models.IntegerField(default=30, help_text="Seconds per question")
    total_questions = models.IntegerField(default=10)

    # Scoring rules (configurable per quiz/round)
    points_correct = models.IntegerField(default=10)
    points_wrong = models.IntegerField(default=0,
                                       help_text="Use negative value e.g. -5 for buzzer penalty")
    speed_bonus_enabled = models.BooleanField(default=False,
                                              help_text="Enable for Speed Round")
    speed_bonus_max = models.IntegerField(default=5,
                                         help_text="Max extra points for fastest answer")

    # Live Stage rules (for finals)
    is_live_mode = models.BooleanField(default=False, help_text="Enable Host-controlled Live Stage mode")
    current_question = models.ForeignKey('Question', on_delete=models.SET_NULL, null=True, blank=True, related_name='active_in_quizzes')
    current_question_start_time = models.DateTimeField(null=True, blank=True)
    LIVE_STATUS_CHOICES = [
        ('waiting', 'Waiting to Start'),
        ('question_active', 'Question Active (Accepting Answers)'),
        ('answer_revealed', 'Answer Revealed'),
        ('leaderboard', 'Showing Leaderboard'),
        ('finished', 'Quiz Finished')
    ]
    live_status = models.CharField(max_length=20, choices=LIVE_STATUS_CHOICES, default='waiting')

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.title} [{self.get_quiz_type_display()}]"


class Question(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()
    image = models.ImageField(upload_to='question_images/', blank=True, null=True,
                              help_text="For Image/Diagram Identification round")
    option_a = models.CharField(max_length=255)
    option_b = models.CharField(max_length=255)
    option_c = models.CharField(max_length=255)
    option_d = models.CharField(max_length=255)
    correct_option = models.CharField(max_length=1,
                                      help_text="A, B, C or D")
    explanation = models.TextField(blank=True,
                                   help_text="Shown after answer — great for learning moments")
    order = models.IntegerField(default=0)

    def __str__(self):
        return f"Q{self.order}: {self.text[:60]}"


class Attempt(models.Model):
    """One attempt per participant per quiz. Guests get their own attempt."""
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE,
                                    null=True, blank=True, related_name='attempts')
    guest = models.ForeignKey(GuestPlayer, on_delete=models.CASCADE,
                              null=True, blank=True, related_name='attempts')
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')
    score = models.IntegerField(default=0)
    speed_bonus_total = models.IntegerField(default=0)
    completed = models.BooleanField(default=False)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        # A registered user can only attempt each quiz once
        constraints = [
            models.UniqueConstraint(
                fields=['participant', 'quiz'],
                condition=models.Q(participant__isnull=False),
                name='unique_participant_quiz'
            )
        ]

    @property
    def total_score(self):
        return self.score + self.speed_bonus_total

    @property
    def player_name(self):
        if self.participant:
            return self.participant.user.get_full_name() or self.participant.user.username
        if self.guest:
            return self.guest.display_name
        return "Unknown"

    def __str__(self):
        return f"{self.player_name} — {self.quiz.title} ({self.total_score} pts)"


class Answer(models.Model):
    attempt = models.ForeignKey(Attempt, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_option = models.CharField(max_length=1)
    is_correct = models.BooleanField()
    time_taken = models.IntegerField(default=0, help_text="Seconds taken to answer")
    speed_bonus = models.IntegerField(default=0, help_text="Bonus points awarded for speed")

    def __str__(self):
        status = "✓" if self.is_correct else "✗"
        return f"{status} {self.question.text[:40]}"


# ─── TEAMS ────────────────────────────────────────────────────────────────────

class Team(models.Model):
    name = models.CharField(max_length=50)
    color = models.CharField(max_length=20, blank=True,
                             help_text="Optional team color for display e.g. #FF5733")
    total_score = models.IntegerField(default=0,
                                      help_text="Updated live during finals")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def recalculate_score(self):
        """Recalculate from all member attempts on final quizzes."""
        from django.db.models import Sum
        members = self.members.values_list('participant', flat=True)
        agg = Attempt.objects.filter(
            participant__in=members,
            quiz__quiz_type='final'
        ).aggregate(s=Sum('score'), b=Sum('speed_bonus_total'))
        
        total = (agg['s'] or 0) + (agg['b'] or 0)
        self.total_score = total
        self.save(update_fields=['total_score'])


class TeamMember(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='members')
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE,
                                    related_name='team_membership')

    class Meta:
        unique_together = ('team', 'participant')

    def __str__(self):
        return f"{self.participant} → {self.team}"


# ─── LEADERBOARD ──────────────────────────────────────────────────────────────

class Leaderboard(models.Model):
    """
    One row per player per quiz.
    Supports both registered participants and guests (for daily quiz).
    """
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE,
                                    null=True, blank=True, related_name='leaderboard_entries')
    guest = models.ForeignKey(GuestPlayer, on_delete=models.CASCADE,
                              null=True, blank=True, related_name='leaderboard_entries')
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='leaderboard')
    score = models.IntegerField(default=0)
    speed_bonus = models.IntegerField(default=0)
    rank = models.IntegerField(default=0)
    date = models.DateField(default=timezone.now)

    class Meta:
        ordering = ['-score', '-speed_bonus']

    @property
    def total_score(self):
        return self.score + self.speed_bonus

    @property
    def player_name(self):
        if self.participant:
            return self.participant.user.get_full_name() or self.participant.user.username
        if self.guest:
            return self.guest.display_name
        return "Unknown"

    @property
    def player_level(self):
        if self.participant:
            return self.participant.level
        return "—"

    def __str__(self):
        return f"{self.player_name}: {self.total_score} pts"


# ─── DAILY QUIZ EVENT CONFIG ──────────────────────────────────────────────────

class DailyEvent(models.Model):
    """
    Maps each HOD Games day to a sport theme.
    Admin creates these once; the daily quiz links to it.
    """
    day_number = models.IntegerField(unique=True)
    title = models.CharField(max_length=100, help_text="E.g. 'Football Day'")
    emoji = models.CharField(max_length=5, blank=True, help_text="E.g. ⚽")
    event_date = models.DateField()
    quiz = models.OneToOneField(Quiz, on_delete=models.SET_NULL,
                                null=True, blank=True, related_name='daily_event')

    class Meta:
        ordering = ['day_number']

    def __str__(self):
        return f"Day {self.day_number}: {self.title} {self.emoji}"