import os

from celery import Celery

from app.core.config import settings

REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = os.getenv("REDIS_PORT")

celery_app = Celery(
    'ecampus_tasks',
    broker=f'redis://{REDIS_HOST}:{REDIS_PORT}/0',
    backend=f'redis://{REDIS_HOST}:{REDIS_PORT}/0',
    include=[
        'app.tasks.quiz_tasks',
        'app.tasks.note_tasks'
    ]
)


celery_app.conf.update(
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    timezone='Asia/Seoul',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=1600, 
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=10,
    
    # ✅ DB backend 설정
    result_backend_transport_options={
        'master_name': 'mymaster',
    },
    database_table_names={
        'task': 'celery_taskmeta',
        'group': 'celery_groupmeta',
    }
)