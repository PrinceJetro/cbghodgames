import os
import django
from datetime import date

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'brainbattle.settings')
django.setup()

from main.models import Quiz, Question

# Create qualifier quizzes
levels = ['100', '200', '300', '400']
for level in levels:
    quiz = Quiz.objects.create(
        title=f'Qualifier Quiz - {level}L',
        quiz_type='qualifier',
        level=level,
        is_active=True,
        time_limit=30,
        total_questions=10
    )

    # Sample questions
    questions_data = [
        {
            'text': f'What is the capital of France?',
            'options': ['Paris', 'London', 'Berlin', 'Madrid'],
            'correct': 'A'
        },
        {
            'text': f'What is 2 + 2?',
            'options': ['3', '4', '5', '6'],
            'correct': 'B'
        },
        {
            'text': f'What color is the sky?',
            'options': ['Red', 'Blue', 'Green', 'Yellow'],
            'correct': 'B'
        },
        {
            'text': f'How many continents are there?',
            'options': ['5', '6', '7', '8'],
            'correct': 'C'
        },
        {
            'text': f'What is the largest planet?',
            'options': ['Earth', 'Mars', 'Jupiter', 'Saturn'],
            'correct': 'C'
        },
        {
            'text': f'What is H2O?',
            'options': ['Water', 'Oxygen', 'Hydrogen', 'Carbon'],
            'correct': 'A'
        },
        {
            'text': f'What year is it?',
            'options': ['2023', '2024', '2025', '2026'],
            'correct': 'D'
        },
        {
            'text': f'What is the square root of 16?',
            'options': ['2', '3', '4', '5'],
            'correct': 'C'
        },
        {
            'text': f'Who wrote Romeo and Juliet?',
            'options': ['Shakespeare', 'Dickens', 'Austen', 'Hemingway'],
            'correct': 'A'
        },
        {
            'text': f'What is the chemical symbol for gold?',
            'options': ['Go', 'Gd', 'Au', 'Ag'],
            'correct': 'C'
        }
    ]

    for q_data in questions_data:
        Question.objects.create(
            quiz=quiz,
            text=q_data['text'],
            option_a=q_data['options'][0],
            option_b=q_data['options'][1],
            option_c=q_data['options'][2],
            option_d=q_data['options'][3],
            correct_option=q_data['correct']
        )

# Create daily quiz
daily_quiz = Quiz.objects.create(
    title='Daily Quiz - Football Day',
    quiz_type='daily',
    date=date.today(),
    is_active=True,
    time_limit=30,
    total_questions=5
)

daily_questions = [
    {
        'text': 'Which level scored the highest goals today?',
        'options': ['100L', '200L', '300L', '400L'],
        'correct': 'A'
    },
    {
        'text': 'Who won the final match?',
        'options': ['Team A', 'Team B', 'Team C', 'Draw'],
        'correct': 'B'
    },
    {
        'text': 'How many matches were played?',
        'options': ['5', '10', '15', '20'],
        'correct': 'B'
    },
    {
        'text': 'Which team conceded the least goals?',
        'options': ['Alpha', 'Beta', 'Gamma', 'Delta'],
        'correct': 'A'
    },
    {
        'text': 'What was the highest scoring game?',
        'options': ['1-0', '2-1', '3-2', '4-3'],
        'correct': 'D'
    }
]

for q_data in daily_questions:
    Question.objects.create(
        quiz=daily_quiz,
        text=q_data['text'],
        option_a=q_data['options'][0],
        option_b=q_data['options'][1],
        option_c=q_data['options'][2],
        option_d=q_data['options'][3],
        correct_option=q_data['correct']
    )

print("Sample data created successfully!")