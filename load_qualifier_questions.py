import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'brainbattle.settings')
django.setup()

from main.models import Quiz, Question

def load_data():
    json_path = os.path.join(os.path.dirname(__file__), 'grand_final_questions.json')
    
    if not os.path.exists(json_path):
        print(f"File not found: {json_path}")
        return

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    quizzes_data = data.get('quizzes', [])
    for q_data in quizzes_data:
        # Check if quiz already exists based on title and level
        quiz, created = Quiz.objects.update_or_create(
            title=q_data['title'],
            level=q_data['level'],
            defaults={
                'quiz_type': q_data.get('quiz_type', 'qualifier'),
                'round_type': q_data.get('round_type', 'standard'),
                'is_active': q_data.get('is_active', True),
                'time_limit': q_data.get('time_limit', 30),
                'total_questions': q_data.get('total_questions', len(q_data.get('questions', []))),
                'points_correct': q_data.get('points_correct', 10),
                'points_wrong': q_data.get('points_wrong', 0),
                'speed_bonus_enabled': q_data.get('speed_bonus_enabled', False),
                'speed_bonus_max': q_data.get('speed_bonus_max', 5),
            }
        )
        if created:
            print(f"Created Quiz: {quiz.title}")
        else:
            print(f"Updated Quiz: {quiz.title}")
            
        questions_list = q_data.get('questions', [])
        loaded_q_count = 0
        for question_data in questions_list:
            question, q_created = Question.objects.update_or_create(
                quiz=quiz,
                text=question_data['text'],
                defaults={
                    'option_a': question_data['option_a'],
                    'option_b': question_data['option_b'],
                    'option_c': question_data['option_c'],
                    'option_d': question_data['option_d'],
                    'correct_option': question_data['correct_option'],
                    'explanation': question_data.get('explanation', ''),
                    'order': question_data.get('order', 0)
                }
            )
            if q_created:
                loaded_q_count += 1
                
        print(f"Loaded/Updated {len(questions_list)} questions for {quiz.title} (New: {loaded_q_count})")

if __name__ == '__main__':
    print("Starting data load...")
    load_data()
    print("Data load complete!")
