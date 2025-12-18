import base64
import hashlib
import json
import math
import os
import pathlib
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
from dotenv import load_dotenv
from moviepy import VideoFileClip
from openai import OpenAI
from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

# PDF
from reportlab.platypus import BaseDocTemplate, Flowable, Frame
from reportlab.platypus import Image as RLImage
from reportlab.platypus import (
    KeepInFrame,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# -------------------- 사용자 설정 --------------------
# VIDEO_FILE           = "./downloads/04 Spatial & Frequency Domain Approaches_02.mp4"
VIDEO_FILE = os.getenv("VIDEO_FILE")
# WORKDIR              = "./khunote_mp4_run"
WORKDIR = os.getenv("WORKDIR")
MODE = os.getenv("MODE", "quiz") 

if not VIDEO_FILE or not WORKDIR:
    raise ValueError("VIDEO_FILE과 WORKDIR 환경변수는 필수입니다")

CHUNK_SECONDS        = 600
KEYFRAME_THRESHOLD   = 45.0
KEYFRAME_INTERVAL    = 30
STT_MODEL            = "gpt-4o-mini-transcribe"   # 음성 → 텍스트
LLM_MODEL            = "gpt-4o-mini"  
MAX_IMAGES_PER_CALL  = 6
LANG                 = "ko"
PDF_INCLUDE_IMAGES   = True
# MODE                 = "quiz"   # summary / blank / quiz 중 선택
QUIZ_ALLOW_SHORT_ANSWER = True  

os.makedirs(WORKDIR, exist_ok=True)
load_dotenv()
client = OpenAI()
pdfmetrics.registerFont(UnicodeCIDFont('HYSMyeongJo-Medium'))

# 시스템 프롬프트
def load_system_prompt(path: str) -> str:
    if not os.path.exists(path):
        raise FileNotFoundError(f"시스템 프롬프트를 찾을 수 없습니다: {path}\n현재 작업 디렉토리: {os.getcwd()}")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()
    
SYSTEM_PROMPT_PATH = "/app/scripts/system_prompts/visual_audio_summary_prompt.txt"
SYSTEM_PROMPT_VISUAL = load_system_prompt(SYSTEM_PROMPT_PATH)

# ------------------ Fonts ------------------
pdfmetrics.registerFont(UnicodeCIDFont('HYSMyeongJo-Medium'))

# ------------------ Data structures ------------------
@dataclass
class ImagePaths:
    page_to_path: Dict[int, str]

# -------------------- 유틸 --------------------
def build_image_map(pages_dir: Optional[str]) -> Optional[ImagePaths]:
    """
    Scan pages_dir for files like page_0001.jpg and return {1: path, 2: path, ...}
    """
    if not pages_dir or not os.path.isdir(pages_dir):
        return None
    page_to_path = {}
    for name in sorted(os.listdir(pages_dir)):
        m = re.match(r"page_(\d{4})\.(jpg|jpeg|png)$", name, re.I)
        if m:
            pnum = int(m.group(1))
            page_to_path[pnum] = os.path.join(pages_dir, name)
    return ImagePaths(page_to_path=page_to_path)

def fill_defaults(obj: dict, lang: str = "ko") -> dict:
    obj.setdefault("meta", {})
    meta = obj["meta"]
    meta.setdefault("title", "Lecture Summary")
    meta.setdefault("course", "")
    meta.setdefault("date", "")
    meta.setdefault("language", lang)

    obj.setdefault("style", {"section_rule": True, "tables": {"header_color":"#EAF3FF","zebra_stripe":True}})
    obj.setdefault("summaries", {"standard": {"sections":[]}})
    std = obj["summaries"].setdefault("standard", {})
    std.setdefault("sections", [])
    # optional helpers for blank-mode
    std.setdefault("glossary", [])
    std.setdefault("checklist", [])

    obj.setdefault("references", [])
    obj.setdefault("highlight_pages", [])
    return obj

def _nonempty_tier(t: dict) -> bool:
    return bool(t) and isinstance(t.get("sections", []), list) and len(t["sections"]) > 0

# ------------------ Layout helpers ------------------

class FixedImage(RLImage):
    """
    ReportLab Image with safe wrap that returns the pre-set drawWidth/drawHeight, avoiding mis-read EXIF.
    """
    def __init__(self, filename, width=None, height=None, **kw):
        try:
            self._img_data = ImageReader(filename)
            original_w, original_h = self._img_data.getSize()
        except Exception:
            self._img_data = None
            original_w, original_h = (1, 1)

        if width is None and height is None:
            width, height = 1*mm, 1*mm
        elif width is None:
            width = height / original_h * original_w
        elif height is None:
            height = width / original_w * original_h

        self.drawWidth, self.drawHeight = width, height
        super().__init__(filename, width=self.drawWidth, height=self.drawHeight, **kw)

    def wrap(self, availWidth, availHeight):
        return self.drawWidth, self.drawHeight

def human_time(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

def to_data_uri(image_path: str) -> str:
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    ext = pathlib.Path(image_path).suffix.lower().replace(".", "")
    mime = "jpeg" if ext in ("jpg", "jpeg") else "png"
    return f"data:image/{mime};base64,{b64}"

def _try_json_autofix(s: str):
    import json
    import re
    t = s.strip()
    # 코드펜스 제거
    t = re.sub(r"^```(json)?\s*|\s*```$", "", t, flags=re.S)
    # 바깥 { ... }만 추출
    i, j = t.find("{"), t.rfind("}")
    if i == -1 or j == -1 or j <= i:
        return None
    t = t[i:j+1]
    # 홑따옴표 -> 큰따옴표 (키/값에 한정)
    t = re.sub(r"\'([A-Za-z0-9_\-]+)\'\s*:", r'"\1":', t)
    t = re.sub(r':\s*\'([^\'\\]*)\'', r': "\1"', t)
    # 트레일링 콤마 제거
    t = re.sub(r",\s*([\}\]])", r"\1", t)
    try:
        return json.loads(t)
    except:
        return None

def _save_json(path: str, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

# -------------------- 1) 오디오 분할 --------------------
def split_audio_chunks(video_path: str, output_dir: str, chunk_seconds: int) -> List[str]:
    clip = VideoFileClip(video_path)
    audio = clip.audio
    duration = int(clip.duration)
    print(f"▶ 영상 길이: {human_time(duration)} ({duration}s)")
    os.makedirs(output_dir, exist_ok=True)
    paths = []
    for start in range(0, duration, chunk_seconds):
        end = min(start + chunk_seconds, duration)
        sub = audio.subclipped(start, end)
        out = os.path.join(output_dir, f"chunk_{start:06d}_{end:06d}.wav")
        if not os.path.exists(out):  # 이미 있으면 재생성 생략 (조용히 덮어쓰지 않음)
            sub.write_audiofile(out, fps=16000, codec="pcm_s16le")
        paths.append(out)
    clip.close()
    return paths

# -------------------- 2) STT --------------------
def stt_chunk(wav_path: str, model: str = STT_MODEL, lang: str = LANG) -> str:
    with open(wav_path, "rb") as f:
        resp = client.audio.transcriptions.create(
            model=model, file=f, language=lang
        )
    return resp.text or ""

def transcribe_all(audio_paths: List[str]) -> List[Dict]:
    results = []
    for p in audio_paths:
        m = re.search(r"chunk_(\d+)_(\d+)\.wav$", os.path.basename(p))
        start = int(m.group(1)) if m else 0
        end   = int(m.group(2)) if m else 0
        print(f"▶ STT: {os.path.basename(p)} [{human_time(start)} ~ {human_time(end)}]")
        text = stt_chunk(p)
        results.append({"start": start, "end": end, "text": text})
    return results

# -------------------- 3) 키프레임 --------------------
def extract_keyframes_with_timestamps(video_path: str, output_dir: str, threshold=50.0, interval_sec=30) -> List[Tuple[str,int]]:
    os.makedirs(output_dir, exist_ok=True)
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    interval_frames = int(fps * interval_sec)
    ret, prev_frame = cap.read()
    if not ret: return []
    prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
    frame_count, keyframe_count = 0, 0
    outputs, last_ts = [], -999
    while True:
        ret, frame = cap.read()
        if not ret: break
        frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        diff = cv2.absdiff(frame_gray, prev_gray)
        non_zero = np.sum(diff) / diff.size
        ts = int(frame_count / fps)
        save = False
        if non_zero > threshold or frame_count % interval_frames == 0:
            if ts - last_ts > 5:   # 너무 가까운 프레임 중복 방지
                save = True
        if save:
            out = os.path.join(output_dir, f"key_{keyframe_count:04d}_{ts}s.jpg")
            cv2.imwrite(out, frame)
            outputs.append((out, ts))
            keyframe_count += 1
            last_ts = ts
        prev_gray, frame_count = frame_gray, frame_count+1
    cap.release()
    print(f"▶ 키프레임: {keyframe_count}장 추출")
    return outputs

# -------------------- 4) 텍스트 전처리 --------------------
def normalize_text(text: str) -> str:
    text = text.replace("\u3000"," ").replace("\xa0"," ")
    text = re.sub(r"[ \t]+"," ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def split_paragraphs(text: str) -> List[str]:
    text = normalize_text(text)
    paras = re.split(r"(?:\n\s*\n)|(?:\.\s*\n)", text)
    return [p.strip() for p in paras if p.strip()]

def detect_titles(paras: List[str]) -> List[str]:
    out=[]
    for p in paras:
        if re.match(r"^(\d+(\.\d+)*)[)\.\s-]+", p) or len(p)<50:
            out.append(f"**{p}**")
        else:
            out.append(p)
    return out

def _attach_section_images_from_indices(obj: dict,
                                        keyframe_paths: List[str],
                                        min_importance: str = "high",
                                        max_per_section: int = 1) -> dict:
    """
    LLM이 반환한 섹션별 images: [{"index": i, "importance": "...", "caption": "..."}]
    -> 실제 파일 경로로 치환하여 images_files: [{"path": "...", "caption": "..."}]
    importance 필터: 기본 high만, 섹션당 최대 max_per_section개.
    """
    importance_rank = {"low":0, "medium":1, "high":2}
    thr = importance_rank.get(min_importance, 2)

    summaries = obj.get("summaries", {})
    std = summaries.get("standard", {})
    sections = std.get("sections", [])
    for sec in sections:
        picked = []
        for it in (sec.get("images") or []):
            try:
                idx = int(it.get("index", -1))
                imp = str(it.get("importance", "low")).lower()
                if idx < 1 or idx > len(keyframe_paths):
                    continue
                if importance_rank.get(imp, 0) < thr:
                    continue
                path = keyframe_paths[idx-1]  # 1-based -> 0-based
                picked.append({"path": path, "caption": it.get("caption")})
            except Exception:
                continue
        # 섹션당 최대 개수 제한
        picked = picked[:max_per_section]
        if picked:
            sec["images_files"] = picked  # 렌더러가 소비할 필드
    return obj

# -------------------- 5) 프롬프트 --------------------
AGG_PROMPT_BASE = (
    "아래는 슬라이드 페이지별 요약입니다. 이를 바탕으로 요청된 산출물을 만들어 주세요.\n"
    "공통 규칙:\n"
    "- 수식은 LaTeX $...$ 형식 유지\n"
    "- 기술 용어/고유명사는 영어 그대로 유지(Fourier, Laplacian, SVD 등)\n"
    "- 글머리표 다양화(•, –, ①, ② ...)\n"
    "- 반복/군더더기 제거, 시험 대비 핵심 우선\n"
    "- (스타일 의도) 섹션 구분선/표 헤더 연한 하늘색(#EAF3FF)/표 지브라, 제목 아래 한 줄 공백을 염두에 두고 서술\n"
    "- (이미지 선택) 텍스트 이해에 실질적 도움 될 때만 이미지를 언급하고, 장식/중복은 배제\n"
    "- 중요 페이지를 판단해 highlight_pages(정수 배열)도 JSON으로 함께 제시\n"
    "입력은 p1..pN 형태의 마크다운 블록이며, 각 블록 끝에는 is_critical 메모가 있을 수 있습니다.\n"
)
def prompt_summary(paras: List[str]) -> str:
    return (
        SYSTEM_PROMPT_VISUAL + "\n\n" +
        AGG_PROMPT_BASE +
        "\n[요청]\n"
        "아래 페이지 요약을 바탕으로 **요약 노트(JSON)** 한 개 객체로만 출력하라. 스키마는 다음과 같다:\n"
        "{\n"
        '  "meta": { "title": "string", "course": "string", "date": "string", "language": "ko" },\n'
        '  "style": { "section_rule": true, "heading_spacing_after": "1-line", "tables": {"header_color":"#EAF3FF","zebra_stripe":true}, "layout":{"avoid_manual_pagebreaks":true,"compact":true} },\n'
        '  "summaries": {\n'
        '    "standard": { "sections": [ {\n'
        '        "h2":"string", "paragraphs":["..."], "bullets":["..."],\n'
        '        "tables":[{"title":"string","columns":["..."],"rows":[["..."]]}],\n'
        '        "images":[ {"index": 1, "importance":"high|medium|low", "caption":"선택"} ]\n'
        '    } ] }\n'
        "  },\n"
        '  "highlight_pages": []\n'
        "}\n"
        "- **첨부된 이미지(키프레임)는 입력 순서대로 1..K 번호가 매겨졌다고 가정**하고, 각 섹션의 이해에 실질적 도움이 되는 **중요한 이미지만** `images`에 포함하라.\n"
        "- 과도한 중복 제거, 수식은 $...$ 유지, 기술 용어 영어 유지.\n"
        "\n[입력 원본(페이지 요약)]\n"
        + "\n".join(paras[:300])
    )

def prompt_blank(paras: List[str], min_clozes: int) -> str:
    return (
        SYSTEM_PROMPT_VISUAL + "\n\n" +
        AGG_PROMPT_BASE +
        "\n[요청]\n"
        f"**[최우선 목표]** 아래 페이지 요약을 바탕으로 시험 대비 **핵심 용어 빈칸 채우기 문제(clozes)**를 최소 {min_clozes}개 이상 **반드시 생성**해야 합니다.\n"
        "대학 강의 **요약 노트**를 아래 JSON 스키마로만 출력하라(한 개 JSON 객체). 스키마의 summaries 필드는 clozes 배열을 채우기 위한 내용 참조 용도로 사용되며, clozes 배열 채우기가 최우선입니다:\n"
        "{\n"
        '  "meta": { "title": "string", "course": "string", "date": "string", "language": "ko" },\n'
        '  "style": { "section_rule": true, "heading_spacing_after": "1-line", "tables": {"header_color":"#EAF3FF","zebra_stripe":true}, "layout":{"avoid_manual_pagebreaks":true,"compact":true} },\n'
        '  "summaries": {\n'
        '    "short":    { "sections": [ { "h2":"string", "paragraphs":["..."], "bullets":["..."] } ], "glossary":[["용어","설명"]], "checklist":["..."] },\n'
        '    "standard": { "sections": [ { "h2":"string", "paragraphs":["..."], "bullets":["..."] } ], "glossary":[["용어","설명"]], "checklist":["..."] },\n'
        '    "detailed": { "sections": [ { "h2":"string", "paragraphs":["..."], "bullets":["..."] } ], "glossary":[["용어","설명"]], "checklist":["..."] }\n'
        "  },\n"
        '  "clozes": [ { "text": "문장 ____ 로 가린 부분", "answer": "정답"} ],\n'
        "}\n"
        "\n[입력 원본(페이지 요약)]\n"
        + "\n".join(paras[:300])
    )

def prompt_quiz(paras: List[str], min_clozes: int, allow_short_answer: bool) -> str:
    base = SYSTEM_PROMPT_VISUAL + "\n\n" + AGG_PROMPT_BASE + "\n[요청]\n"

    if allow_short_answer:
        # ✅ 객관식 + 단답형 혼합 모드
        schema = (
            "**예상 문제 세트(JSON)** 한 개 객체로만 출력하라:\n"
            "{\n"
            '  "meta": { "title": "string", "course": "string", "date": "string", "language": "ko" },\n'
            '  "multiple_choice": [\n'
            '    { "q": "질문 문장", "options": ["보기1","보기2","보기3","보기4"], '
            '"answer_index": 1, "explanation": "선택/있으면 간단한 해설" }\n'
            "  ],\n"
            '  "short_answer": [\n'
            '    { "q": "단답형 질문 문장", '
            '"a": "정답(한 단어 또는 짧은 구)", '
            '"answer_length": 5, '
            '"rubric": "채점 기준/핵심 키워드 (선택)" }\n'
            "  ]\n"
            "}\n"
            f"- 최소 {min_clozes}문항 이상 출제하되, multiple_choice와 short_answer를 모두 포함하고 "
            "둘 다 1문항 이상이 되도록 구성하라.\n"
            "- short_answer는 **반드시 '단어' 또는 '짧은 구(phrase)' 수준의 답**이 나오도록 할 것.\n"
            "  - 예: 용어 이름, 기법 이름, 구성 요소 이름, 하나의 수식 이름 등.\n"
            "  - **설명형 문장(예: '~을 의미한다', '~하는 기법이다')을 a에 쓰지 말 것.**\n"
            "  - a는 가능하면 명사/명사구 형태로만 작성하라.\n"
            "- short_answer의 q는\n"
            "  - \"~를 무엇이라고 하나요?\", \"~를 가리키는 용어는?\", \"~의 이름은?\"처럼\n"
            "    **정답이 용어 하나로 떨어지도록 질문을 재구성**하라.\n"
            "- short_answer의 answer_length는\n"
            "  - a에 들어가는 실제 글자 수(공백 제외, 한글 기준)를 정수로 적는다.\n"
            "  - 예: a가 \"파이프라인 플러시\"라면 answer_length는 8.\n"
        )
    else:
        # ✅ 객관식만 출제 모드
        schema = (
            "**예상 문제 세트(JSON)** 한 개 객체로만 출력하라:\n"
            "{\n"
            '  "meta": { "title": "string", "course": "string", "date": "string", "language": "ko" },\n'
            '  "multiple_choice": [\n'
            '    { "q": "질문 문장", "options": ["보기1","보기2","보기3","보기4"], '
            '"answer_index": 1, "explanation": "선택/있으면 간단한 해설" }\n'
            "  ]\n"
            "}\n"
            f"- multiple_choice 배열에는 반드시 {min_clozes}문항 이상 포함되어야 한다. "
             "- **{min_clozes}문항 미만일 경우 이는 명백한 규칙 위반이다.**\n"
            "**단답형(short_answer)은 만들지 말 것. 오직 multiple_choice만 생성**하라.\n"
        )

    common_rules = (
        "- 모든 문항은 이 강의의 내용(슬라이드/설명)만을 기반으로 한다.\n"
        "- multiple_choice는 개념 구분/비교/정의 확인 위주로 출제한다.\n"
        "- 보기(options)는 서로 충분히 헷갈릴 수 있도록 구성하되, 명백히 틀린 선택지는 넣지 않는다.\n"
        "- 모든 텍스트는 한국어로 작성하라.\n"
        "- 먼저 이 강의에서 출제 가능한 핵심 개념을 목록으로 15개 이상 내부적으로 정리한 뒤,\n"
        "- 그 개념 각각에 대해 하나의 객관식 문제를 생성하라.\n"
        "- 최종 산출물은 반드시 유효한 JSON 하나만 출력하고, 마크다운/코드블록/추가 설명 문장은 넣지 말 것.\n"
        "\n[입력 원본(페이지 요약)]\n"
    )

    return base + schema + common_rules + "\n".join(paras[:300])

# -------------------- 6) GPT 호출 --------------------
def call_gpt_json(
    text_prompt: str,
    images: List[str],
    system_prompt: str = SYSTEM_PROMPT_VISUAL,
    *,
    max_output_tokens: int = 5000,     # 출력 길이 상한 ↑
    temperature: float = 0.2,          # 요약 안정적
    top_p: float = 0.9,
    min_sections: int = 6,             # 분량 가드레일(미충족 시 1회 재시도)
    min_glossary: int = 12,
    min_checklist: int = 10,
    retries: int = 1                   # 부족하면 한 번 더 보강 요청
) -> dict:
    """
    - SYSTEM_PROMPT_VISUAL을 system 메시지로 항상 포함
    - 출력 토큰 상한/샘플링 파라미터 설정
    - 결과가 너무 빈약하면(섹션/글로서리/체크리스트 최소치 미달) 1회 보강 재시도
    - SDK 응답 스키마 차이를 고려한 안전 파싱
    """
    def _make_messages(extra_hint: str = ""):
        sys_content = [{"type": "input_text", "text": (system_prompt or "").strip()}]
        # 필요하면 추가 힌트(보강 지시) 붙이기
        user_text = text_prompt if not extra_hint else (text_prompt + "\n\n" + extra_hint)
        user_content = [{"type": "input_text", "text": user_text}]
        for p in images[:MAX_IMAGES_PER_CALL]:
            user_content.append({"type": "input_image", "image_url": to_data_uri(p)})
        return [
            {"role": "system", "content": sys_content},
            {"role": "user", "content": user_content},
        ]

    def _extract_text(resp) -> str:
        # SDK 버전차 안전 추출
        out = getattr(resp, "output_text", None)
        if out is not None:
            return out
        try:
            return resp.output[0].content[0].text
        except Exception:
            return ""

    def _is_poor(obj: dict) -> bool:
        try:
            std = (obj.get("summaries") or {}).get("standard") or {}
            sections = std.get("sections") or []
            glossary = std.get("glossary") or []
            checklist = std.get("checklist") or []
            if len(sections) < min_sections: return True
            if len(glossary) < min_glossary: return True
            if len(checklist) < min_checklist: return True
            return False
        except Exception:
            # JSON 구조가 어긋나면 보강 시도
            return True

    # 1차 시도
    messages = _make_messages()
    resp = client.responses.create(
        model=LLM_MODEL,
        input=messages,
        max_output_tokens=max_output_tokens,
        temperature=temperature,
        top_p=top_p,
    )
    raw_text = _extract_text(resp)

    try:
        obj = json.loads(raw_text)
    except Exception:
        fixed = _try_json_autofix(raw_text)
        obj = fixed if fixed is not None else {"raw": raw_text}

    # 분량 부족하면 1회 보강 재시도
    if retries > 0 and isinstance(obj, dict) and _is_poor(obj):
        booster = (
            "⚠️ 분량 보강:\n"
            f"- 섹션 최소 {min_sections}개(각 섹션 문단≥3, 불릿≥5)\n"
            f"- glossary 최소 {min_glossary}개, checklist 최소 {min_checklist}개\n"
            "- 표 최소 2개(비교/절차/장단점), 수식 $...$ 유지\n"
            "- 외부 지식으로 정의/예시/응용 자유 보강(주제와 직접 관련)\n"
            "- 반드시 유효 JSON만 출력(스키마 불일치 시 자체 복구)"
        )
        messages = _make_messages(extra_hint=booster)
        resp = client.responses.create(
            model=LLM_MODEL,
            input=messages,
            max_output_tokens=max_output_tokens,
            temperature=temperature,
            top_p=top_p,
        )
        raw_text2 = _extract_text(resp)
        try:
            obj2 = json.loads(raw_text2)
        except Exception:
            fixed2 = _try_json_autofix(raw_text2)
            obj2 = fixed2 if fixed2 is not None else {"raw": raw_text2}
        # 보강본이 낫다면 교체
        if not isinstance(obj, dict) or _is_poor(obj):
            obj = obj2

    return obj
# 동영상 캐시 저장
def _video_signature(video_path: str) -> dict:
    """영상의 식별 정보를 만들어 캐시 키로 사용."""
    ap = os.path.abspath(video_path)
    try:
        st = os.stat(ap)
        size = st.st_size
        mtime = int(st.st_mtime)
    except FileNotFoundError:
        size = -1
        mtime = -1
    key = f"{os.path.basename(ap)}__{size}__{mtime}"
    # 경로까지 섞어서 64 길이의 안정 키도 만들자(폴더명 충돌 방지)
    strong = hashlib.sha1((ap + "|" + key).encode("utf-8")).hexdigest()
    return {"abs": ap, "size": size, "mtime": mtime, "key": key, "strong": strong}

def _load_stt_cache(json_path: str, sig: dict) -> Optional[list]:
    """캐시 JSON이 있고 시그니처가 맞으면 results를 반환."""
    if not os.path.exists(json_path):
        return None
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            obj = json.load(f)
        meta = obj.get("meta", {})
        ok = (
            meta.get("video_abs") == sig["abs"] and
            meta.get("video_size") == sig["size"] and
            meta.get("video_mtime") == sig["mtime"]
        )
        if ok and isinstance(obj.get("results"), list):
            print("▶ STT 캐시 적중: 기존 결과를 재사용합니다.")
            return obj["results"]
    except Exception:
        pass
    return None

def _save_stt_cache(json_path: str, sig: dict, results: list, chunk_seconds: int, stt_model: str):
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    payload = {
        "meta": {
            "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "video_abs": sig["abs"],
            "video_size": sig["size"],
            "video_mtime": sig["mtime"],
            "sig_key": sig["key"],
            "sig_sha1": sig["strong"],
            "chunk_seconds": chunk_seconds,
            "stt_model": stt_model,
        },
        "results": results,
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"✅ STT 캐시 저장: {json_path}")   


# -------------------- 7) PDF 출력 --------------------
def render_pdf_from_json(json_path: str,
                         outpath: str,
                         images: Optional[ImagePaths],
                         include_images: bool,
                         dpi: int,
                         max_thumb_w_mm: float,
                         max_thumb_h_mm: float,
                         mode: str):
    # Load JSON
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    data = fill_defaults(data, lang=data.get("meta", {}).get("language", "ko"))
    summaries = data.get("summaries", {})
    tier = None
    # # Doc & styles
    # doc = SimpleDocTemplate(
    #     outpath, pagesize=A4,
    #     leftMargin=16*mm, rightMargin=16*mm,
    #     topMargin=16*mm, bottomMargin=16*mm
    # )
    # styles = getSampleStyleSheet()
    # styles.add(ParagraphStyle(name="BodyKR", parent=styles["Normal"], fontName="HYSMyeongJo-Medium", fontSize=10, leading=14))
    # styles.add(ParagraphStyle(name="H2KR", parent=styles["Heading2"], fontName="HYSMyeongJo-Medium", spaceAfter=6))
    # styles.add(ParagraphStyle(name="SmallGrey", parent=styles["Normal"], fontName="HYSMyeongJo-Medium", fontSize=8, textColor=colors.grey))
    # styles.add(ParagraphStyle(name="Caption", parent=styles["Normal"], fontName="HYSMyeongJo-Medium", fontSize=8, textColor=colors.grey, spaceBefore=1, spaceAfter=2))

    # story: List[Flowable] = []
    
    for cand in ("standard", "detailed", "short"):
        t = summaries.get(cand)
        if _nonempty_tier(t):
            tier = t
            break
    if tier is None:
        tier = {"sections": []}

    # Header
    meta = data.get("meta", {})
    title = meta.get("title", "Lecture Summary")
    course = meta.get("course", "")
    date = meta.get("date", "")
    # story.append(Paragraph(title, styles["Heading1"]))
    # sub = " · ".join([x for x in [course, date] if x])
    # if sub:
    #     story.append(Paragraph(sub, styles["SmallGrey"]))
    # story.append(Spacer(1, 6*mm))

    style_cfg = data.get("style", {})
    rule_on = style_cfg.get("section_rule", True)
    table_cfg = style_cfg.get("tables", {"header_color":"#EAF3FF","zebra_stripe":True})

    C = {
        "brand": colors.HexColor("#1F6FEB"),
        "brand_light": colors.HexColor("#EAF3FF"),
        "card_bg": colors.HexColor("#F7FAFF"),
        "muted": colors.HexColor("#6B7280"),
        "rule": colors.HexColor("#E5E7EB"),
        "caption": colors.HexColor("#6B7280"),
        "table_grid": colors.HexColor("#D1D5DB"),
    }

    PAGE_W, PAGE_H = A4
    M = 16*mm
    header_h = 16*mm
    footer_h = 12*mm
    frame = Frame(M, M+footer_h, PAGE_W-2*M, PAGE_H - (header_h + footer_h) - 2*M, id="content")

        # ---------- 헤더/푸터 ----------
    def draw_header_footer(canvas, doc):
        canvas.saveState()
        # Header bar line
        canvas.setStrokeColor(C["rule"])
        canvas.line(M, PAGE_H - M - header_h + 2*mm, PAGE_W - M, PAGE_H - M - header_h + 2*mm)

        # Title / meta
        canvas.setFont("HYSMyeongJo-Medium", 12)
        canvas.setFillColor(colors.black)
        canvas.drawString(M, PAGE_H - M - header_h + 6*mm, title[:80])

        canvas.setFont("HYSMyeongJo-Medium", 8)
        canvas.setFillColor(C["muted"])
        meta_line = " · ".join([x for x in [course, date] if x])
        if meta_line:
            canvas.drawRightString(PAGE_W - M, PAGE_H - M - header_h + 6*mm, meta_line[:90])

        # Footer: page number
        canvas.setFont("HYSMyeongJo-Medium", 8)
        canvas.setFillColor(C["muted"])
        canvas.drawRightString(PAGE_W - M, M + 3*mm, str(canvas.getPageNumber()))

        canvas.restoreState()

    doc = BaseDocTemplate(outpath, pagesize=A4,
                          leftMargin=M, rightMargin=M, topMargin=M, bottomMargin=M)
    template = PageTemplate(id="main", frames=[frame],
                            onPage=draw_header_footer)
    doc.addPageTemplates([template])

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="H2KR", parent=styles["Heading2"],
                              fontName="HYSMyeongJo-Medium",
                              spaceBefore=0, spaceAfter=4, leading=16))
    styles.add(ParagraphStyle(name="BodyKR", parent=styles["Normal"],
                              fontName="HYSMyeongJo-Medium",
                              fontSize=10, leading=14))
    styles.add(ParagraphStyle(name="SmallGrey", parent=styles["Normal"],
                              fontName="HYSMyeongJo-Medium",
                              fontSize=8, textColor=C["muted"]))
    styles.add(ParagraphStyle(name="Caption", parent=styles["Normal"],
                              fontName="HYSMyeongJo-Medium",
                              fontSize=8, textColor=C["caption"],
                              spaceBefore=2, spaceAfter=2))

    def section_rule():
        if not rule_on:
            return Spacer(1, 2*mm)
        tbl = Table([[""]], colWidths=[doc.width])
        tbl.setStyle(TableStyle([
            ("LINEBELOW", (0,0), (-1,-1), 0.5, colors.HexColor("#DDDDDD")),
            ("LEFTPADDING",(0,0),(-1,-1),0), ("RIGHTPADDING",(0,0),(-1,-1),0),
            ("TOPPADDING",(0,0),(-1,-1),2), ("BOTTOMPADDING",(0,0),(-1,-1),6),
        ]))
        return tbl

    def table_from_spec(spec: dict):
        cols = spec.get("columns", [])
        rows = spec.get("rows", [])
        data_tbl = [cols] + rows
        t = Table(data_tbl, hAlign="LEFT")
        header_color = colors.HexColor(table_cfg.get("header_color", "#EAF3FF"))
        ts = [
            ("BACKGROUND", (0,0), (-1,0), header_color),
            ("TEXTCOLOR", (0,0), (-1,0), colors.black),
            ("FONTNAME", (0,0), (-1,-1), "HYSMyeongJo-Medium"),
            ("ALIGN", (0,0), (-1,0), "CENTER"),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
            ("LEFTPADDING", (0,0), (-1,-1), 6),
            ("RIGHTPADDING", (0,0), (-1,-1), 6),
            ("TOPPADDING", (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 6),
            ("GRID", (0,0), (-1,-1), 0.25, C["table_grid"]),
        ]
        if table_cfg.get("zebra_stripe", True):
            for r in range(1, len(data_tbl)):
                if r % 2 == 1:
                    ts.append(("BACKGROUND", (0,r), (-1,r), colors.whitesmoke))
        t.setStyle(TableStyle(ts))
        flows = []
        if spec.get("title"):
            flows.append(Paragraph(spec["title"], styles["SmallGrey"]))
        flows.append(t)
        return flows
    
    def bullet_flows(items: list):
        flows = []
        for it in items:
            flows.append(Paragraph(f"• {it}", styles["BodyKR"]))
        return flows
    
    def section_card(title_text: str, body_flows: list):
        header_tbl = Table(
            [[Paragraph(title_text, styles["H2KR"])]],
            style=TableStyle([
                ("BACKGROUND", (0,0), (-1,-1), C["card_bg"]),
                ("LEFTPADDING",(0,0),(-1,-1), 8),
                ("RIGHTPADDING",(0,0),(-1,-1), 8),
                ("TOPPADDING",(0,0),(-1,-1), 6),
                ("BOTTOMPADDING",(0,0),(-1,-1), 4),
                ("LINEABOVE",(0,0),(-1,-1), 0.6, C["brand_light"]),
                ("LINEBELOW",(0,0),(-1,-1), 0.6, C["brand_light"]),
            ]),
            colWidths=[doc.width]
        )

        # 너무 긴 본문은 작은 덩어리로 나눠 일부만 KeepTogether
        def chunk(flows, n=8):
            for i in range(0, len(flows), n):
                yield flows[i:i+n]

        flows_out = [header_tbl, Spacer(1, 2*mm)]
        for group in chunk(body_flows, n=8):
            # 소그룹만 KeepTogether — 페이지 끝에서 예쁜 분리
            flows_out.append(KeepTogether(group))
        flows_out.append(Spacer(1, 6*mm))
        return flows_out

    def append_section_thumbnails_from_images_files(sec: dict):
        """
        sec["images_files"] 기준으로 작은 썸네일(필요 시에만)을 섹션 뒤에 붙인다.
        - 한 섹션당 0~N장 (이미지 존재할 때만)
        - 썸네일 크기: max_thumb_w_mm x max_thumb_h_mm
        - 캡션: images_files[i]["caption"] 사용
        """
        if not include_images:
            return []

        thumbs = []
        for im in sec.get("images_files", []):
            img_path = im.get("path")
            caption  = im.get("caption")
            if not img_path or not os.path.exists(img_path):
                continue

            # 썸네일 크기 계산
            try:
                with PILImage.open(img_path) as pil:
                    w, h = pil.size or (1, 1)
                    aspect = h / float(w) if w else 1.0
                    target_w = max_thumb_w_mm * mm
                    target_h = max_thumb_h_mm * mm
                    draw_w = target_w
                    draw_h = target_w * aspect
                    if draw_h > target_h:
                        draw_h = target_h
                        draw_w = target_h / aspect
            except Exception:
                # 이미지 깨질 경우 캡션만
                thumbs.append(Paragraph("[이미지 로드 실패]", styles["Caption"]))
                continue

            img_flow = FixedImage(img_path, width=draw_w, height=draw_h)
            thumbs.extend([
                Paragraph(caption or "관련 슬라이드", styles["Caption"]),
                KeepInFrame(target_w, target_h, [img_flow], mode="shrink"),
                Spacer(1, 4*mm),
            ])

        return thumbs
    
    story: List[Flowable] = []
    
    # ---------- sections ----------
    if mode == "summary":
        for sec in tier.get("sections", []):
            h = (sec.get("h2") or "Untitled").strip()
            paragraphs = sec.get("paragraphs", []) or []
            bullets = sec.get("bullets", []) or []
            tables = sec.get("tables", []) or []

            body = []
            body.append(section_rule())
            for p in paragraphs:
                body.append(Paragraph(p, styles["BodyKR"]))
                body.append(Spacer(1, 1*mm))

            body.extend(bullet_flows(bullets))

            for tspec in tables:
                body.extend(table_from_spec(tspec))
                body.append(Spacer(1, 2*mm))
                
            # 카드로 묶어서 추가
            story.extend(section_card(h, body))
        

            thumbs = append_section_thumbnails_from_images_files(sec)
            if thumbs:
                story.extend(thumbs)


    # ---------- glossary ----------
    std = summaries.get("standard", {}) if isinstance(summaries, dict) else {}
    glossary = data.get("glossary", []) or std.get("glossary", [])
    checklist = data.get("checklist", []) or std.get("checklist", [])
    refs = data.get("references", [])

    if glossary and mode == "summary":
        story.append(Spacer(1, 4*mm))
        story.extend(section_card("용어 정리 (Glossary)", [
            Table(
                [[Paragraph(c or "", styles["BodyKR"]) for c in row] for row in glossary],
                colWidths=[doc.width*0.3, doc.width*0.7],
                style=TableStyle([
                    ('FONTNAME', (0,0), (-1,-1), 'HYSMyeongJo-Medium'),
                    ('VALIGN', (0,0), (-1,-1), 'TOP'),
                    ('GRID', (0,0), (-1,-1), 0.25, C["table_grid"]),
                    ('LEFTPADDING', (0,0), (-1,-1), 6),
                    ('RIGHTPADDING', (0,0), (-1,-1), 6),
                    ('TOPPADDING', (0,0), (-1,-1), 4),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                ])
            )
        ]))

    if checklist and mode == "summary":
        flows = []
        for item in checklist:
            flows.append(Paragraph(f"⬜ {item}", styles["BodyKR"]))
            flows.append(Spacer(1, 1*mm))
        story.extend(section_card("확인 목록 (Checklist)", flows))

    # ---------- clozes(빈칸 채우기) 문제 ----------

    if mode == "blank":
        clozes = data.get("clozes", [])
        if isinstance(clozes, list) and clozes:
            flows = []
            for i, c in enumerate(clozes, 1):
                qtext = (c.get("text") or "").strip()
                if not qtext:
                    continue
                flows.append(Paragraph(f"{i}. {qtext}", styles["BodyKR"]))
                flows.append(Spacer(1, 1*mm))
            if flows:
                story.extend(section_card("빈칸 채우기 문제 (Cloze)", flows))


    # ---------- answer sheet (blank mode) ----------
    if mode == "blank":
        clozes = data.get("clozes") or []
        if isinstance(clozes, list) and clozes:
            story.append(PageBreak())
            story.append(Paragraph("정답 모음", styles["H2KR"]))
            if rule_on:
                story.append(section_rule())
            for i, c in enumerate(clozes, start=1):
                ans_text = (c.get("answer") or "").strip()
                if not ans_text:
                    continue
                story.append(Paragraph(f"{i}. {ans_text}", styles["BodyKR"]))
                story.append(Spacer(1, 1*mm))
    else:
        ans = data.get("answer_sheet")
        if isinstance(ans, dict) and ans.get("items"):
            story.append(PageBreak())
            story.append(Paragraph(ans.get("title", "정답 모음"), styles["H2KR"]))
            if rule_on:
                story.append(section_rule())
            for it in ans["items"]:
                story.append(Paragraph(it, styles["BodyKR"]))
    # Build
    doc.build(story)
    print(f"✅ PDF 저장 완료: {outpath}")

def export_stt_text(video_file: str, workdir: str, out_txt: str):
    import hashlib
    import json
    import os

    def _video_signature(video_path: str):
        ap = os.path.abspath(video_file)
        st = os.stat(ap)
        key = f"{os.path.basename(ap)}__{st.st_size}__{int(st.st_mtime)}"
        strong = hashlib.sha1((ap + "|" + key).encode("utf-8")).hexdigest()
        return {"strong": strong}

    def hms(t):
        m, s = divmod(int(t), 60); h, m = divmod(m, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    sig = _video_signature(video_file)
    cache_path = os.path.join(workdir, "stt_cache", f"stt_{sig['strong']}.json")
    if not os.path.exists(cache_path):
        raise FileNotFoundError(f"STT 캐시가 없습니다: {cache_path}\n스크립트를 한 번 실행해 STT를 생성하세요.")

    with open(cache_path, "r", encoding="utf-8") as f:
        obj = json.load(f)

    results = sorted(obj.get("results", []), key=lambda r: r.get("start", 0))
    with open(out_txt, "w", encoding="utf-8") as w:
        for r in results:
            start, end, text = r.get("start", 0), r.get("end", 0), (r.get("text") or "").strip()
            w.write(f"[{hms(start)}–{hms(end)}]\n{text}\n\n")
    print(f"✅ STT 텍스트 내보내기 완료: {out_txt}")

# 키프레임과 텍스트 매칭칭
def build_page_blocks(stt_results: List[Dict], keyframes: List[Tuple[str,int]], fanout_sec: int = 30) -> List[Tuple[str, str, bool]]:
    """
    keyframes: [(img_path, ts_sec), ...]
    반환: [(title, text, is_critical), ...]  title은 "p{i} [t0~t1]" 형식
    """
    if not keyframes:
        # 키프레임 없으면 통으로 한 블록
        text = "\n".join(r["text"] for r in stt_results if r.get("text"))
        return [("p1 [0~end]", text.strip(), False)]
    
    page_blocks = build_page_blocks(stt_results, keyframes, fanout_sec=30)
    
    # 키프레임 경계 시각 만들기
    times = [ts for _, ts in keyframes]
    bounds = [0] + [max(0, ts - fanout_sec) for ts in times] + [max(r["end"] for r in stt_results)]
    # 구간별 STT 수집
    blocks = []
    for i in range(1, len(bounds)):
        t0, t1 = bounds[i-1], bounds[i]
        chunk = []
        for r in stt_results:
            if r["end"] <= t0 or r["start"] >= t1:
                continue
            chunk.append(r["text"])
        txt = normalize_text(" ".join(chunk))
        title = f"p{i} [{human_time(t0)}~{human_time(t1)}]"
        # 매우 짧은 블록은 critical 아님
        is_critical = len(txt.split()) > 60
        blocks.append((title, txt, is_critical))
    return blocks

# -------------------- 실행 --------------------
def main():
    if not os.path.exists(VIDEO_FILE):
        raise FileNotFoundError(f"영상 없음: {VIDEO_FILE}")

    clip = VideoFileClip(VIDEO_FILE)
    duration_sec = int(clip.duration or 0)
    clip.close()
    min_clozes = max(10, math.ceil((duration_sec / 3600) * 10))  # 1시간당 10문제, 최소 10
    print(f"min_clozes = {min_clozes}")
    
    # 시그니처/경로 설정
    sig = _video_signature(VIDEO_FILE)
    audio_dir = os.path.join(WORKDIR, "audio_chunks", sig["strong"])  # 영상별로 분리
    stt_cache_json = os.path.join(WORKDIR, "stt_cache", f"stt_{sig['strong']}.json")

    # 1) audio chunk 단위로 자르기 -> stt 적용(캐시 있으면 그걸로 대체체)
    stt_results = _load_stt_cache(stt_cache_json, sig)
    if stt_results is None:
        # 캐시 없음 → 청크 생성 + STT
        audio_paths = split_audio_chunks(VIDEO_FILE, audio_dir, CHUNK_SECONDS)
        stt_results = transcribe_all(audio_paths)
        _save_stt_cache(stt_cache_json, sig, stt_results, CHUNK_SECONDS, STT_MODEL)
    else:
        # 캐시가 있으면 청크 디렉토리도 확인(없어도 상관 없으나 있으면 재활용 가능)
        if not os.path.isdir(audio_dir):
            print("※ 참고: 오디오 청크 폴더가 없어 STT만 재사용합니다. (문제 없음)")

    # 2) stt text 전처리
    text_all = "\n".join([r["text"] for r in stt_results])
    paras = detect_titles(split_paragraphs(text_all))
    export_stt_text(VIDEO_FILE, WORKDIR, os.path.join(WORKDIR, "KHUNote_stt.txt"))
    # 3) keyframe 추출
    keyframes = extract_keyframes_with_timestamps(VIDEO_FILE, os.path.join(WORKDIR,"keyframes"), KEYFRAME_THRESHOLD, KEYFRAME_INTERVAL)
    keyframe_paths = [k[0] for k in keyframes]

    if MODE=="summary":
        prompt = prompt_summary(paras)
        obj = call_gpt_json(prompt, keyframe_paths, system_prompt = SYSTEM_PROMPT_VISUAL)
        obj.setdefault("meta", {})["note_type"] = "summary"
        
        obj = _attach_section_images_from_indices(            # index -> 파일경로로 치환(+중요도 필터)
        obj, keyframe_paths,
        min_importance="high",        # high만 사용 (원하면 "medium"으로 완화)
        max_per_section=1             # 섹션당 최대 1장
        )
        json_path = os.path.join(WORKDIR, "KHUNote_summary.json")
        _save_json(json_path, obj)
        render_pdf_from_json(
            json_path=json_path,
            outpath=os.path.join(WORKDIR, "KHUNote_summary.pdf"),
            images=None,                    # 페이지/슬라이드 썸네일 연동 안 쓸 때
            include_images=True,           # 위와 동일
            dpi=150,
            max_thumb_w_mm=70,
            max_thumb_h_mm=60,
            mode = "summary",
        )

    elif MODE == "blank":
        prompt = prompt_blank(paras, min_clozes=min_clozes)
        obj = call_gpt_json(prompt, keyframe_paths, system_prompt = SYSTEM_PROMPT_VISUAL)
        obj.setdefault("meta", {})["note_type"] = "blank"
        
        clozes = obj.get("clozes", [])
        if isinstance(clozes, list) and clozes:
            answer_items = []
            for i, c in enumerate(clozes, 1):
                qtext = (c.get("text") or "").strip()
                ans = (c.get("answer") or "").strip()
                item_str = f"{i}. {ans}"
                if qtext:
                    item_str += f"    ←  {qtext}"
                answer_items.append(item_str)

            obj["answer_sheet"] = {
                "title": "정답 모음 (빈칸 채우기 Cloze Answers)",
                "items": answer_items,
            }
        
        json_path = os.path.join(WORKDIR, "KHUNote_blank.json")
        _save_json(json_path, obj)

        render_pdf_from_json(
            json_path=json_path,
            outpath=os.path.join(WORKDIR, "KHUNote_blank.pdf"),
            images=None,
            include_images=False,
            dpi=150,
            max_thumb_w_mm=70,
            max_thumb_h_mm=60,
            mode = "blank",
        )
        
    elif MODE=="quiz":
        allow_short_answer = QUIZ_ALLOW_SHORT_ANSWER
        prompt = prompt_quiz(paras, min_clozes=min_clozes, allow_short_answer=allow_short_answer)
        obj = call_gpt_json(
            prompt,
            keyframe_paths,
            system_prompt=SYSTEM_PROMPT_VISUAL,
            min_sections=0,
            min_glossary=0,
            min_checklist=0,
        )
        
        if not isinstance(obj, dict):
            obj = {"raw": obj}

        obj.setdefault("meta", {})["note_type"] = "quiz"
        
        json_path = os.path.join(WORKDIR, "KHUNote_quiz.json")
        _save_json(json_path, obj)
        print(f"✅ 예상문제 JSON 저장 완료: {json_path}")

if __name__=="__main__":
    main()
