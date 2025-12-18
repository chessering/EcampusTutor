# app/tasks/__init__.py
from app.tasks.quiz_tasks import generate_quiz_task, generate_quiz_from_url_task

__all__ = [
    'generate_quiz_task', 
    'generate_quiz_from_url_task',
    'generate_summary_task',
    'generate_summary_from_url_task'
]