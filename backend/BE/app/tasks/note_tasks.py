# app/tasks/note_tasks.py
import json
import os
import subprocess
import sys
import time
from typing import List

from PyPDF2 import PdfMerger

from app.celery_config import celery_app
from app.core.config import settings


@celery_app.task(bind=True, name='generate_summary_from_files')
def generate_summary_task(
    self,
    user_id: int,
    files: List[str],
    mode: str  # "summary" | "blank"
):
    """
    PDF 파일로 요약/빈칸 노트 생성
    """
    try:
        self.update_state(
            state='PROCESSING',
            meta={'progress': 10, 'status': 'PDF 병합 중...'}
        )
        
        # 1. Job 디렉토리 생성
        job_id = f"note_{user_id}_{int(time.time())}"
        output_dir = os.path.join(settings.SUMMARY_WORKDIR, f"job_{job_id}")
        os.makedirs(output_dir, exist_ok=True)
        
        # 2. 파일 병합 (여러 PDF → 하나)
        if len(files) > 1:
            merged_pdf = os.path.join(output_dir, "merged_input.pdf")
            _merge_pdfs_sync(files, merged_pdf)
            pdf_input = merged_pdf
        else:
            pdf_input = files[0]
        
        self.update_state(
            state='PROCESSING',
            meta={'progress': 30, 'status': 'GPT API로 변환 중...'}
        )
        
        # 3. 외부 스크립트 실행
        pdf_path = _run_pdf_script_sync(pdf_input, output_dir, mode)
        
        self.update_state(
            state='PROCESSING',
            meta={'progress': 90, 'status': '완료 처리 중...'}
        )
        
        # 4. 결과 반환
        pdf_filename = os.path.basename(pdf_path)
        pdf_url = f"/api/notes/download/{job_id}/{pdf_filename}"
        
        result_data = {
            'status': 'COMPLETED',
            'pdf_url': pdf_url,
            'job_id': job_id
        }
        
        print("=" * 60)
        print("🎉 [NOTE TASK COMPLETE]")
        print(f"  job_id: {job_id}")
        print(f"  pdf_url: {pdf_url}")
        print(f"  mode: {mode}")
        print("=" * 60)
        
        return result_data
        
    except Exception as e:
        print("=" * 60)
        print(f"🔥 Note Task Error: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        print("=" * 60)
        
        return {
            'status': 'FAILED',
            'error': str(e)
        }
    
    finally:
        # 임시 파일 정리
        print(f"🧹 임시 파일 정리: {len(files)}개")
        for f in files:
            try:
                if os.path.exists(f):
                    os.remove(f)
                    print(f"  ✅ {os.path.basename(f)}")
            except Exception as e:
                print(f"  ⚠️ {os.path.basename(f)}: {e}")


@celery_app.task(bind=True, name='generate_summary_from_url')
def generate_summary_from_url_task(
    self,
    user_id: int,
    url: str,
    canvas_id: str,
    canvas_password: str,
    mode: str  # "summary" | "blank"
):
    """
    Canvas URL로 요약/빈칸 노트 생성
    """
    try:
        self.update_state(
            state='PROCESSING',
            meta={'progress': 10, 'status': 'Canvas 동영상 다운로드 중...'}
        )
        
        # 1. Job 디렉토리 생성
        job_id = f"note_{user_id}_{int(time.time())}"
        output_dir = os.path.join(settings.SUMMARY_WORKDIR, f"job_{job_id}")
        os.makedirs(output_dir, exist_ok=True)
        
        # 2. Canvas에서 동영상 다운로드
        video_path = _download_video_sync(
            url=url,
            output_dir=output_dir,
            canvas_id=canvas_id,
            canvas_password=canvas_password
        )
        
        self.update_state(
            state='PROCESSING',
            meta={'progress': 50, 'status': 'GPT API로 변환 중...'}
        )
        
        # 3. 동영상 → PDF
        pdf_path = _run_video_script_sync(video_path, output_dir, mode)
        
        self.update_state(
            state='PROCESSING',
            meta={'progress': 90, 'status': '완료 처리 중...'}
        )
        
        # 4. 결과 반환
        pdf_filename = os.path.basename(pdf_path)
        pdf_url = f"/api/notes/download/{job_id}/{pdf_filename}"
        
        result_data = {
            'status': 'COMPLETED',
            'pdf_url': pdf_url,
            'job_id': job_id
        }
        
        print("=" * 60)
        print("🎉 [URL NOTE TASK COMPLETE]")
        print(f"  job_id: {job_id}")
        print(f"  pdf_url: {pdf_url}")
        print(f"  mode: {mode}")
        print("=" * 60)
        
        return result_data
        
    except Exception as e:
        print("=" * 60)
        print(f"🔥 URL Note Task Error: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        print("=" * 60)
        
        return {
            'status': 'FAILED',
            'error': str(e)
        }


# ========== Helper Functions ==========

def _merge_pdfs_sync(files: List[str], output_path: str):
    """동기 PDF 병합"""
    merger = PdfMerger()
    
    for pdf_file in files:
        if not os.path.exists(pdf_file):
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {pdf_file}")
        merger.append(pdf_file)
    
    merger.write(output_path)
    merger.close()
    print(f"✅ {len(files)}개 PDF를 하나로 합침: {output_path}")


def _run_pdf_script_sync(pdf_input: str, output_dir: str, mode: str) -> str:
    """
    PDF → 요약/빈칸 노트 생성 스크립트 실행 (동기)
    mode: "summary" | "blank"
    """
    if not os.path.exists(pdf_input):
        raise FileNotFoundError(f"입력 PDF가 존재하지 않습니다: {pdf_input}")
    
    env = os.environ.copy()
    env.update({
        "PDF_FILE": pdf_input,
        "WORKDIR": output_dir,
        "MODE": mode,
        "LANG": "ko",
        "OPENAI_API_KEY": settings.OPENAI_API_KEY
    })
    
    pdf_script = settings.PDF_SCRIPT_PATH
    python_exec = sys.executable
    
    print(f"🚀 PDF 스크립트 실행: {pdf_script}")
    print(f"   Mode: {mode}")
    print(f"   Input: {pdf_input}")
    print(f"   Output: {output_dir}")
    
    result = subprocess.run(
        [python_exec, pdf_script],
        env=env,
        capture_output=True,
        text=True,
        timeout=settings.PDF_TIMEOUT
    )
    
    print(f"📄 [PDF STDOUT]: {result.stdout}")
    print(f"📄 [PDF STDERR]: {result.stderr}")
    
    if result.returncode != 0:
        raise Exception(f"PDF 변환 실패: {result.stderr}")
    
    # 생성된 PDF 찾기
    pdf_files = [
        f for f in os.listdir(output_dir)
        if f.endswith(".pdf") and mode in f.lower()
    ]
    
    if not pdf_files:
        raise Exception("PDF 생성 실패: 출력 파일을 찾을 수 없습니다")
    
    result_path = os.path.join(output_dir, pdf_files[0])
    print(f"✅ PDF 생성 완료: {result_path}")
    return result_path


def _run_video_script_sync(video_path: str, output_dir: str, mode: str) -> str:
    """
    동영상 → 요약/빈칸 노트 생성 스크립트 실행 (동기)
    mode: "summary" | "blank"
    """
    env = os.environ.copy()
    env.update({
        "VIDEO_FILE": video_path,
        "WORKDIR": output_dir,
        "MODE": mode,
        "LANG": "ko",
        "OPENAI_API_KEY": settings.OPENAI_API_KEY
    })
    
    url_script = settings.URL_SCRIPT_PATH
    python_exec = sys.executable
    
    print(f"🚀 동영상 스크립트 실행: {url_script}")
    print(f"   Mode: {mode}")
    print(f"   Input: {video_path}")
    print(f"   Output: {output_dir}")
    
    result = subprocess.run(
        [python_exec, url_script],
        env=env,
        capture_output=True,
        text=True,
        timeout=settings.VIDEO_TIMEOUT
    )
    
    print(f"📄 [VIDEO STDOUT]: {result.stdout}")
    print(f"📄 [VIDEO STDERR]: {result.stderr}")
    
    if result.returncode != 0:
        raise Exception(f"동영상 변환 실패: {result.stderr}")
    
    # 생성된 PDF 찾기
    pdf_files = [
        f for f in os.listdir(output_dir)
        if f.endswith(".pdf") and mode in f.lower()
    ]
    
    if not pdf_files:
        raise Exception("PDF 생성 실패: 출력 파일을 찾을 수 없습니다")
    
    result_path = os.path.join(output_dir, pdf_files[0])
    print(f"✅ PDF 생성 완료: {result_path}")
    return result_path


def _download_video_sync(
    url: str,
    output_dir: str,
    canvas_id: str,
    canvas_password: str
) -> str:
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
    
    print(f"📥 Canvas 동영상 다운로드 시작: {url}")
    
    result = subprocess.run(
        [python_exec, canvas_script],
        env=env,
        capture_output=True,
        text=True,
        timeout=300  # 5분
    )
    
    print(f"📄 [DOWNLOAD STDOUT]: {result.stdout}")
    print(f"📄 [DOWNLOAD STDERR]: {result.stderr}")
    
    if result.returncode != 0:
        raise Exception(f"동영상 다운로드 실패: {result.stderr}")
    
    # 다운로드된 mp4 찾기
    video_files = [f for f in os.listdir(output_dir) if f.endswith(".mp4")]
    
    if not video_files:
        raise Exception("동영상 파일을 찾을 수 없습니다")
    
    video_path = os.path.join(output_dir, video_files[0])
    print(f"✅ 동영상 다운로드 완료: {video_path}")
    return video_path