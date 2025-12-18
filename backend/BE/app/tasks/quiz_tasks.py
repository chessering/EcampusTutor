# app/tasks/quiz_tasks.py
import json
import os
import subprocess
import sys
from typing import Dict, List

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.celery_config import celery_app
from app.core.config import settings
from app.model.question import Question
from app.model.quiz import Quiz
from app.model.user import User


@celery_app.task(bind=True, name='generate_quiz_from_files')
def generate_quiz_task(
    self, 
    quiz_id: int, 
    user_id: int, 
    files: List[str], 
    include_short_answer: bool
):
    """
    PDF 파일로 퀴즈 생성
    """
    # 동기 DB 세션
    engine = create_engine(
        settings.DATABASE_URL.replace('postgresql+asyncpg', 'postgresql')
    )
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        self.update_state(
            state='PROCESSING',
            meta={'progress': 10, 'status': 'PDF 병합 중...'}
        )
        
        # 1. 파일 병합 (여러 PDF → 하나)
        job_id = f"quiz_{quiz_id}_{user_id}"
        output_dir = os.path.join(settings.SUMMARY_WORKDIR, f"job_{job_id}")
        os.makedirs(output_dir, exist_ok=True)
        
        if len(files) > 1:
            merged_pdf = os.path.join(output_dir, "merged_input.pdf")
            _merge_pdfs_sync(files, merged_pdf)
            pdf_input = merged_pdf
        else:
            pdf_input = files[0]
        
        self.update_state(
            state='PROCESSING',
            meta={'progress': 30, 'status': 'GPT API로 문제 생성 중...'}
        )
        
        # 2. GPT API 호출
        json_path = _run_quiz_script_sync(pdf_input, output_dir)
        
        self.update_state(
            state='PROCESSING',
            meta={'progress': 80, 'status': 'DB 저장 중...'}
        )
        
        # 3. JSON 파싱
        print(f"📄 JSON 파일 읽기: {json_path}")
        with open(json_path, 'r', encoding='utf-8') as f:
            result = json.load(f)
        
        questions_data = []
        
        # 객관식 문제
        for q in result.get('multiple_choice', []):
            questions_data.append({
                'questionText': q['q'],
                'questionType': 'MULTIPLE',
                'choices': q['options'],
                'correctAnswer': q['answer_index'],
                'explanation': q.get('explanation', '')
            })
        
        # 단답형 문제
        if include_short_answer:
            for q in result.get('short_answer', []):
                questions_data.append({
                    'questionText': q['q'],
                    'questionType': 'SHORT',
                    'choices': [],
                    'correctAnswer': q['a'],
                    'explanation': q.get('rubric', '')
                })
        
        print(f"📊 총 {len(questions_data)}개 문제 생성됨")
        
        # 4. DB 저장
        quiz = db.query(Quiz).filter(Quiz.quiz_id == quiz_id).first()
        if not quiz:
            raise Exception(f"Quiz not found: quiz_id={quiz_id}")
        
        quiz.status = "COMPLETED"
        quiz.total_questions = len(questions_data)
        
        for i, q in enumerate(questions_data):
            question = Question(
                quiz_id=quiz_id,
                question_number=i + 1,
                question_text=q['questionText'],
                question_type=q['questionType'],
                choices=q.get('choices', []),
                correct_answer=str(q['correctAnswer']),
                explanation=q.get('explanation', '')
            )
            db.add(question)
        
        db.commit()
        print(f"✅ DB 커밋 완료")
        
        # ✅ 반환값 생성
        result_data = {
            'status': 'COMPLETED',
            'quiz_id': int(quiz_id),
            'total_questions': int(len(questions_data))
        }
        
        print("=" * 60)
        print("🎉 [TASK COMPLETE]")
        print(f"  quiz_id: {result_data['quiz_id']}")
        print(f"  total_questions: {result_data['total_questions']}")
        print(f"  status: {result_data['status']}")
        print("=" * 60)
        
        return result_data
        
    except Exception as e:
        db.rollback()
        
        quiz = db.query(Quiz).filter(Quiz.quiz_id == quiz_id).first()
        if quiz:
            quiz.status = "FAILED"
            db.commit()
        
        print("=" * 60)
        print(f"🔥 Task Error: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        print("=" * 60)
        
        error_data = {
            'status': 'FAILED', 
            'error': str(e),
            'quiz_id': int(quiz_id)
        }
        
        return error_data
    
    finally:
        db.close()
        
        # 임시 파일 정리
        print(f"🧹 임시 파일 정리: {len(files)}개")
        for f in files:
            try:
                if os.path.exists(f):
                    os.remove(f)
                    print(f"  ✅ {os.path.basename(f)}")
            except Exception as e:
                print(f"  ⚠️ {os.path.basename(f)}: {e}")


def _merge_pdfs_sync(files: List[str], output_path: str):
    """동기 PDF 병합"""
    from PyPDF2 import PdfMerger
    
    merger = PdfMerger()
    for pdf_file in files:
        if not os.path.exists(pdf_file):
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {pdf_file}")
        merger.append(pdf_file)
    
    merger.write(output_path)
    merger.close()


def _run_quiz_script_sync(pdf_input: str, output_dir: str) -> str:
    """
    기존 pdf_to_quiz.py 스크립트 실행 (동기)
    """
    env = os.environ.copy()
    env.update({
        "PDF_FILE": pdf_input,
        "WORKDIR": output_dir,
        "MODE": "quiz",
        "LANG": "ko",
        "OPENAI_API_KEY": settings.OPENAI_API_KEY
    })
    
    pdf_script = settings.PDF_SCRIPT_PATH
    python_exec = sys.executable
    
    result = subprocess.run(
        [python_exec, pdf_script],
        env=env,
        capture_output=True,
        text=True,
        timeout=settings.PDF_TIMEOUT
    )
    
    if result.returncode != 0:
        raise Exception(f"퀴즈 생성 실패: {result.stderr}")
    
    # 생성된 JSON 찾기
    json_files = [
        f for f in os.listdir(output_dir)
        if f.endswith('.json') and 'quiz' in f.lower()
    ]
    
    if not json_files:
        raise Exception("퀴즈 JSON 파일을 찾을 수 없습니다")
    
    return os.path.join(output_dir, json_files[0])


@celery_app.task(bind=True, name='generate_quiz_from_url')
def generate_quiz_from_url_task(
    self,
    quiz_id: int,
    user_id: int,
    url: str,
    include_short_answer: bool
):
    """
    Canvas URL로 퀴즈 생성 (동영상 다운로드 → 스크립트 실행)
    """
    engine = create_engine(
        settings.DATABASE_URL.replace('postgresql+asyncpg', 'postgresql')
    )
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        self.update_state(
            state='PROCESSING',
            meta={'progress': 5, 'status': '사용자 정보 조회 중...'}
        )
        
        # 1. 사용자 Canvas 인증 정보 가져오기
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user or not user.id or not user.password:
            raise Exception("Canvas 인증 정보가 없습니다")
        
        canvas_pw = settings.fernet.decrypt(user.password.encode()).decode()
        
        self.update_state(
            state='PROCESSING',
            meta={'progress': 10, 'status': 'Canvas 동영상 다운로드 중...'}
        )
        
        # 2. Canvas에서 동영상 다운로드
        job_id = f"quiz_{quiz_id}_{user_id}"
        output_dir = os.path.join(settings.SUMMARY_WORKDIR, f"job_{job_id}")
        os.makedirs(output_dir, exist_ok=True)
        
        video_path = _download_video_sync(
            url=url,
            output_dir=output_dir,
            canvas_id=user.id,
            canvas_password=canvas_pw
        )
        
        self.update_state(
            state='PROCESSING',
            meta={'progress': 40, 'status': 'GPT API로 문제 생성 중...'}
        )
        
        # 3. 동영상 → 퀴즈 생성
        json_path = _run_video_quiz_script_sync(video_path, output_dir, include_short_answer)
        
        self.update_state(
            state='PROCESSING',
            meta={'progress': 80, 'status': 'DB 저장 중...'}
        )
        
        # 4. JSON 파싱
        print(f"📄 JSON 파일 읽기: {json_path}")
        with open(json_path, 'r', encoding='utf-8') as f:
            result = json.load(f)
        
        questions_data = []
        
        # 객관식 문제
        for q in result.get('multiple_choice', []):
            questions_data.append({
                'questionText': q['q'],
                'questionType': 'MULTIPLE',
                'choices': q['options'],
                'correctAnswer': q['answer_index'],
                'explanation': q.get('explanation', '')
            })
        
        # 단답형 문제
        if include_short_answer:
            for q in result.get('short_answer', []):
                questions_data.append({
                    'questionText': q['q'],
                    'questionType': 'SHORT',
                    'choices': [],
                    'correctAnswer': q['a'],
                    'explanation': q.get('rubric', '')
                })
        
        print(f"📊 총 {len(questions_data)}개 문제 생성됨")
        
        # 5. DB 저장
        quiz = db.query(Quiz).filter(Quiz.quiz_id == quiz_id).first()
        if not quiz:
            raise Exception(f"Quiz not found: quiz_id={quiz_id}")
        
        quiz.status = "COMPLETED"
        quiz.total_questions = len(questions_data)
        
        for i, q in enumerate(questions_data):
            question = Question(
                quiz_id=quiz_id,
                question_number=i + 1,
                question_text=q['questionText'],
                question_type=q['questionType'],
                choices=q.get('choices', []),
                correct_answer=str(q['correctAnswer']),
                explanation=q.get('explanation', '')
            )
            db.add(question)
        
        db.commit()
        print(f"✅ DB 커밋 완료")
        
        # ✅ 반환값 생성
        result_data = {
            'status': 'COMPLETED',
            'quiz_id': int(quiz_id),
            'total_questions': int(len(questions_data))
        }
        
        print("=" * 60)
        print("🎉 [TASK COMPLETE]")
        print(f"  quiz_id: {result_data['quiz_id']}")
        print(f"  total_questions: {result_data['total_questions']}")
        print(f"  status: {result_data['status']}")
        print("=" * 60)
        
        return result_data
        
    except Exception as e:
        db.rollback()
        
        quiz = db.query(Quiz).filter(Quiz.quiz_id == quiz_id).first()
        if quiz:
            quiz.status = "FAILED"
            db.commit()
        
        print("=" * 60)
        print(f"🔥 URL Task Error: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        print("=" * 60)
        
        error_data = {
            'status': 'FAILED',
            'error': str(e),
            'quiz_id': int(quiz_id)
        }
        
        return error_data
    
    finally:
        db.close()


def _download_video_sync(url: str, output_dir: str, canvas_id: str, canvas_password: str) -> str:
    """
    Canvas에서 동영상 다운로드 (동기)
    """
    env = os.environ.copy()
    env.update({
        "WORKDIR": output_dir,
        "VIDEO_PAGE_URL": url,
        "CANVAS_USERNAME": canvas_id,
        "CANVAS_PASSWORD": canvas_password,
        "LOGIN_PAGE_URL": settings.CANVAS_LOGIN_URL,
    })
    
    canvas_script = settings.CANVAS_DOWNLOADER_PATH
    python_exec = sys.executable
    
    result = subprocess.run(
        [python_exec, canvas_script],
        env=env,
        capture_output=True,
        text=True,
        timeout=1800
    )
    
    if result.returncode != 0:
        raise Exception(f"동영상 다운로드 실패: {result.stderr}")
    
    # 다운로드된 mp4 찾기
    video_files = [f for f in os.listdir(output_dir) if f.endswith(".mp4")]
    if not video_files:
        raise Exception("동영상 파일을 찾을 수 없습니다")
    
    return os.path.join(output_dir, video_files[0])


def _run_video_quiz_script_sync(video_path: str, output_dir: str, include_short_answer: bool) -> str:
    """
    동영상 → 퀴즈 생성 스크립트 실행 (동기)
    """
    env = os.environ.copy()
    env.update({
        "VIDEO_FILE": video_path,
        "WORKDIR": output_dir,
        "MODE": "quiz",
        "LANG": "ko",
        "OPENAI_API_KEY": settings.OPENAI_API_KEY,
        "QUIZ_ALLOW_SHORT_ANSWER": "true" if include_short_answer else "false"
    })
    
    url_script = settings.URL_SCRIPT_PATH
    python_exec = sys.executable
    
    result = subprocess.run(
        [python_exec, url_script],
        env=env,
        capture_output=True,
        text=True,
        timeout=settings.VIDEO_TIMEOUT
    )
    
    if result.returncode != 0:
        raise Exception(f"퀴즈 생성 실패: {result.stderr}")
    
    # 생성된 JSON 찾기
    json_files = [
        f for f in os.listdir(output_dir)
        if f.endswith('.json') and 'quiz' in f.lower()
    ]
    
    if not json_files:
        raise Exception("퀴즈 JSON 파일을 찾을 수 없습니다")
    
    return os.path.join(output_dir, json_files[0])