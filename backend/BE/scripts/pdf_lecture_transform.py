# pdf_lecture_transform.py
import os, re, io, json, time, base64, random
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import math # math 모듈 임포트
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from openai import RateLimitError, APIError

from PIL import Image as PILImage, ImageStat
from pdf2image import convert_from_path

import hashlib

# PDF 출력
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, PageBreak, KeepInFrame
from reportlab.platypus import Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase import pdfmetrics
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader

# ======================== 사용자 설정 ========================
#PDF_FILE            = "./downloads/Computer Architecture_230427-Branch Prediction 2_-_230504_043850.pdf"      # 입력 PDF
# WORKDIR              = "./khunote_pdf_run"
PDF_FILE = os.getenv("PDF_FILE")
WORKDIR = os.getenv("WORKDIR", "./output")
MODE = os.getenv("MODE", "quiz") 
MODEL_VISION         = "gpt-4o-mini"  # 이미지 입력 지원 모델로 통일
LANG                 = "ko"           # "ko" / "en"
# MODE                 = "quiz"      # "summary" | "blank" | "quiz"

if not PDF_FILE:
    raise ValueError("환경변수 PDF_FILE이 설정되지 않았습니다")

if not os.path.exists(PDF_FILE):
    raise FileNotFoundError(f"PDF 파일을 찾을 수 없습니다: {PDF_FILE}")

# POPPLER_PATH         = "../poppler/poppler-25.07.0/Library/bin"  # Windows 예시. macOS/Linux는 None
POPPLER_PATH         = None
DPI                  = 150            # pdf -> image dpi
MAX_WIDTH            = 1280           # 전송 전 이미지 축소 폭
JPEG_QUALITY         = 80             # 전송 전 JPEG 압축 품질
REQUEST_INTERVAL_SEC = 0.35           # 간단 Throttle
MAX_RETRIES          = 6              # 429/5xx 재시도 횟수
BASE_BACKOFF         = 0.8            # 지수 백오프 시작값(초)
MAX_IMAGES_PER_CALL  = 1              # 페이지 단위 호출이므로 1 추천
PDF_INCLUDE_IMAGES   = True           # 요약/빈칸 PDF에 하이라이트 페이지 썸네일 포함
SUMMARY_JSON_PATH   = os.path.join(WORKDIR, "KHUNote_summary.json")
BLANK_JSON_PATH     = os.path.join(WORKDIR, "KHUNote_blank.json")
ALWAYS_CLEAN_PAGES   = False   
MAX_AGGREGATE_PROMPT_BYTES = 200 * 1024 

# ===== JSON 정확성 강화를 위한 설정 =====
ENFORCE_JSON = True             # 통합 요약/빈칸/퀴즈 단계에서 JSON만 받도록 압박
JSON_AUTOFIX = True             # 경미한 JSON 오류(홑따옴표, 트레일링 콤마 등) 자동 복구 시도

# 체크포인트 / 산출물
os.makedirs(WORKDIR, exist_ok=True)
CHECKPOINT_PATH      = os.path.join(WORKDIR, "page_summaries_checkpoint.json")
HIGHLIGHT_JSON_PATH  = os.path.join(WORKDIR, "highlight_pages.json")
SUMMARY_PDF_PATH     = os.path.join(WORKDIR, "KHUNote_summary.pdf")
BLANK_PDF_PATH       = os.path.join(WORKDIR, "KHUNote_blank.pdf")
QUIZ_JSON_PATH       = os.path.join(WORKDIR, "KHUNote_quiz.json")
PAGE_SUMMARIES_JSON_PATH = os.path.join(WORKDIR, "KHUNote_page_summaries.json")

QUIZ_ALLOW_SHORT_ANSWER = True


# 한글 폰트(ReportLab)
pdfmetrics.registerFont(UnicodeCIDFont('HYSMyeongJo-Medium'))

# ===== 실행 산출물 이름 충돌 방지/관리 =====
def unique_path(path: str) -> str:
    """이미 있으면 _1, _2 ... 식으로 유니크 경로 반환"""
    if not os.path.exists(path): 
        return path
    base, ext = os.path.splitext(path)
    i = 1
    while True:
        cand = f"{base}_{i}{ext}"
        if not os.path.exists(cand):
            return cand
        i += 1

RUN_TAG = time.strftime("%Y%m%d-%H%M%S")  # 실행 시각 태그

def with_timestamp(path: str) -> str:
    """파일명에 실행 시각 태그를 자동 부여"""
    base, ext = os.path.splitext(path)
    return f"{base}_{RUN_TAG}{ext}"

def read_text(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""

def write_text(path: str, s: str):
    with open(path, "w", encoding="utf-8") as f:
        f.write(s)

INPUT_HASH_PATH = os.path.join(WORKDIR, "input_pdf_hash.txt")

# OPENAI_API_KEY 사용
load_dotenv()
client = OpenAI()

# ===== 출력 파일명 =====
SUMMARY_JSON_PATH = unique_path(with_timestamp(SUMMARY_JSON_PATH))
BLANK_JSON_PATH   = unique_path(with_timestamp(BLANK_JSON_PATH))
SUMMARY_PDF_PATH  = unique_path(with_timestamp(SUMMARY_PDF_PATH))
BLANK_PDF_PATH    = unique_path(with_timestamp(BLANK_PDF_PATH))
QUIZ_JSON_PATH    = unique_path(with_timestamp(QUIZ_JSON_PATH))

#fixedimage flowable
class FixedImage(Image):
    """
    LayoutError를 피하기 위해 ReportLab의 Image Flowable을 상속받아 wrap 로직을 고정합니다.
    ReportLab이 이미지 메타데이터를 잘못 해석하는 것을 방지합니다.
    """
    def __init__(self, filename, width=None, height=None, **kw):
        # FixedImage를 사용할 때는 filename에 ImageReader 객체가 아닌 파일 경로(str)를 전달해야 합니다.
        
        # 1. ImageReader를 사용하여 이미지 데이터 로드 (ReportLab 내부에서 수행됨)
        # 이 시점에 ReportLab이 파일에서 크기를 읽으려 시도합니다.
        # ImageReader 객체는 이미지가 로드된 상태의 객체를 나타냅니다.
        try:
            self._img_data = ImageReader(filename)
            original_w = self._img_data.getSize()[0]
            original_h = self._img_data.getSize()[1]
        except Exception as e:
            # 이미지 파일이 없거나 잘못된 경우, 안전한 기본값으로 설정
            self._img_data = None
            original_w = 1  # Safe defaults
            original_h = 1

        # 2. 원하는 drawWidth/drawHeight를 계산
        if width is None and height is None:
            # 크기가 지정되지 않았다면, ReportLab이 기본적으로 100% 프레임 너비를 사용하도록 설계할 수도 있지만,
            # 여기서는 안전을 위해 1인치 크기로 기본 설정
            width = 1 * mm
            height = 1 * mm
        elif width is None:
            width = height / original_h * original_w
        elif height is None:
            height = width / original_w * original_h

        self.drawWidth = width
        self.drawHeight = height
        
        # 3. 부모 Image Flowable 초기화: FixedImage의 draw 로직이 drawWidth/drawHeight를 사용하도록 합니다.
        # ReportLab Image는 filename 인자를 받아 내부적으로 ImageReader를 생성합니다.
        super().__init__(filename, width=self.drawWidth, height=self.drawHeight, **kw)
        
        # 4. wrap 로직 고정 (FixedImage의 핵심)
        # self.drawWidth와 self.drawHeight가 이미 설정되었으므로, wrap은 이를 반환합니다.
    def wrap(self, availWidth, availHeight):
        # 🚨 여기서 wrap 메서드가 항상 미리 설정된 고정 크기를 반환하도록 강제합니다.
        # ImageReader 초기화 과정에서 오류가 발생했더라도, 여기서는 오류를 무시하고
        # Table 레이아웃에 필요한 안전한 크기를 제공합니다.
        return self.drawWidth, self.drawHeight

    # wrapOn도 wrap을 호출하도록 설정하여 안정성을 높입니다.
    def wrapOn(self, *args, **kwargs):
        return self.wrap(args[1], kwargs.get('aH', args[-1]))

# ======================== SYSTEM PROMPT 로드 ========================
def load_system_prompt(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

SYSTEM_PROMPT_PATH = Path("/app/scripts/system_prompts/visual_pdf_summary_prompt.txt")
SYSTEM_PROMPT_VISUAL = load_system_prompt(SYSTEM_PROMPT_PATH)

def sha256_str(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

SYSTEM_PROMPT_SIG = sha256_str(SYSTEM_PROMPT_VISUAL) 

def to_data_uri(image_path: str) -> str:
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    ext = Path(image_path).suffix.lower().replace(".", "")
    mime = "jpeg" if ext in ("jpg", "jpeg") else "png"
    return f"data:image/{mime};base64,{b64}"

def _try_json_autofix(s: str):
    import re, json
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

# ======================== 유틸(로그/파일/체크포인트) ========================
def log(msg: str): print(msg, flush=True)

def human_page(i: int, total: int) -> str:
    return f"p{i}/{total}"

def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)
    return path

def load_checkpoint() -> Dict[str, str]:
    if os.path.exists(CHECKPOINT_PATH):
        with open(CHECKPOINT_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_checkpoint(cp: Dict[str, str]):
    with open(CHECKPOINT_PATH, "w", encoding="utf-8") as f:
        json.dump(cp, f, ensure_ascii=False, indent=2)
        
# 🚨 [추가 1] 이미지 경로 관리를 위한 데이터 클래스
@dataclass
class ImagePaths:
    # 1-based page number to image file path
    page_to_path: Dict[int, str]

# ======================== OpenAI 호출 공통 ========================
def call_openai_with_retry(model: str, content_payload: list):
    """429/5xx에 대해 지수 백오프 재시도, 요청 간 간단 대기"""
    attempt = 0
    while True:
        try:
            time.sleep(REQUEST_INTERVAL_SEC)
            resp = client.responses.create(
                model=model,
                input=[{"role":"user","content":content_payload}]
            )
            return resp
        except (RateLimitError, APIError) as e:
            attempt += 1
            if attempt > MAX_RETRIES: raise
            sleep_for = BASE_BACKOFF * (2 ** (attempt-1)) * (1 + random.random()*0.2)
            # 429인 경우 retry-after도 존중
            if isinstance(e, RateLimitError):
                retry_after = getattr(e, "response", None) and e.response.headers.get("retry-after")
                if retry_after:
                    try: sleep_for = float(retry_after)
                    except: pass
            log(f"[WARN] transient error. retry {attempt}/{MAX_RETRIES} after {sleep_for:.2f}s")
            time.sleep(sleep_for)
        except TypeError as e:
            # ✅ 구버전 SDK / 파라미터 미지원 → 즉시 상위 폴백이 시도되도록 재발생
            raise

# ======================== 이미지 전처리/해시 ========================
def shrink_and_encode_image(image_path: str, max_width: int = MAX_WIDTH, jpeg_quality: int = JPEG_QUALITY) -> str:
    """이미지를 가로 max_width로 축소 + JPEG 압축 후 data URI 반환"""
    im = PILImage.open(image_path).convert("RGB")
    w, h = im.size
    if w > max_width:
        new_h = int(h * (max_width / w))
        im = im.resize((max_width, new_h), PILImage.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=jpeg_quality, optimize=True, progressive=True)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{b64}"

def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def average_hash(path: str, hash_size: int = 8) -> str:
    """
    외부 의존성 없이 구현한 aHash (퍼셉추얼 중복 탐지용).
    """
    im = PILImage.open(path).convert("L").resize((hash_size, hash_size))
    pixels = list(im.getdata())
    avg = sum(pixels)/len(pixels)
    bits = "".join("1" if p > avg else "0" for p in pixels)
    # 4비트씩 → hex
    return f"{int(bits, 2):0{hash_size*hash_size//4}x}"

def hamming(a: str, b: str) -> int:
    return bin(int(a, 16) ^ int(b, 16)).count("1")

def prompt_signature(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()

def image_is_mostly_blank(path: str, entropy_threshold: float = 2.2) -> bool:
    """    
    빈/저대비 슬라이드 간이 탐지.
    아주 단순한 빈 슬라이드/저대비 판단(텍스트 거의 없음 추정).
    - entropy가 지나치게 낮으면 빈 페이지로 간주.
    """
    im = PILImage.open(path).convert("L")
    stat = ImageStat.Stat(im)
    # 분산 기반 간이 entropy 추정: log2(1+variance) 근사
    variance = stat.var[0]
    # import math # math는 파일 상단에 이미 임포트되어 있음
    entropy = math.log2(1.0 + variance)
    return entropy < entropy_threshold

# ======================== 1) PDF → 이미지 ========================
def pdf_to_images(pdf_path: str, out_dir: str, dpi: int = DPI, poppler_path: Optional[str] = POPPLER_PATH) -> List[str]:
    ensure_dir(out_dir)
    pages = convert_from_path(pdf_path, dpi=dpi, poppler_path=poppler_path)
    image_paths = []
    for i, im in enumerate(pages, start=1):
        p = os.path.join(out_dir, f"page_{i:04d}.jpg")
        im.convert("RGB").save(p, "JPEG", quality=92)
        image_paths.append(p)
    log(f"▶ PDF → 이미지 변환 완료: {len(image_paths)}p")
    return image_paths

# ======================== SYSTEM PROMPT 프리앰블 주입 ========================
def with_system_preamble(user_prompt: str) -> str:
    """
    로직 변경 없이 system 프롬프트를 텍스트 접두사로 섞음음
    - responses.create(user 역할) 그대로 사용
    - 모델엔 품질/스타일/이미지 선택 규칙을 전달하지만,
      출력 형식은 기존 마크다운(+ 마지막 highlight JSON) 관습 유지
    """
    pre = SYSTEM_PROMPT_VISUAL.strip()
    return f"{pre}\n\n[USER TASK]\n{user_prompt}"


# ======================== 2) 페이지 요약 프롬프트 ========================
def page_summary_prompt(page_index: int, total_pages: int, lang: str = LANG) -> str:
    if lang == "ko":
        return (
            "당신은 대학 강의 조교입니다. 아래 슬라이드 이미지(스캔 품질 포함)를 읽고, 핵심을 과도한 중복 없이 간결하게 요약하세요.\n"
            "필요 시 슬라이드 이미지 이외의 외부 사이트나 자료를 참조하여 내용을 보강할 것. 단, 외부 사이트나 자료는 요약된 내용과 관련이 있어야 하고, 신뢰성이 있어야 함."
            "요구사항:\n"
            "1) 수식은 LaTeX 인라인 표기로 유지: $...$ (예: $H(u,v)=\\frac{1}{1+D(u,v)}$)\n"
            "2) 기술적 용어·고유명사·알고리즘·영문 표기는 영어 그대로 유지(Fourier Transform, Laplacian, SVD 등)\n"
            "3) 글머리표는 다양하게 사용: •, –, ①, ② 등 (하나만 반복하지 않기)\n"
            "4) 불필요한 문장 제거, 핵심 정의/가정/절차/주의점을 우선\n"
            "5) 해당 페이지가 중요한 페이지인지 is_critical(yes/no)와 이유를 마지막에 한 줄로 표시\n"
            "형식 제약: 반드시 '마크다운 텍스트'만 출력할 것. ``` 코드블록, JSON, YAML, HTML은 절대 사용하지 말 것.\n"
            "출력 형식(마크다운):\n"
            f"### p{page_index}/{total_pages}\n"
            "• 핵심 개념:\n"
            "– 주요 정의:\n"
            "① 공식/조건:\n"
            "② 절차/알고리즘:\n"
            "주의/오해 주의:\n"
            "_is_critical: (yes/no, 이유 한 줄)_\n"
        )
    else:
        return (
            "You are a university TA. Read the slide image and produce a concise summary with:\n"
            "1) Keep math in LaTeX $...$\n"
            "2) Preserve English technical terms as-is\n"
            "3) Vary bullets: •, –, ①, ② ...\n"
            "4) Focus on definitions/assumptions/procedures/pitfalls\n"
            "5) End with _is_critical: (yes/no, one-line reason)_\n"
            f"### p{page_index}/{total_pages}\n"
        )

# ======================== 3) 비전 호출(페이지 요약) ========================
def gpt_vision_on_image(prompt_text: str, image_path: str, model: str = MODEL_VISION) -> str:
    prompt_text = with_system_preamble(prompt_text) 
    data_uri = shrink_and_encode_image(image_path, max_width=MAX_WIDTH, jpeg_quality=JPEG_QUALITY)
    content = [
        {"type":"input_text","text":prompt_text},
        {"type":"input_image","image_url":data_uri}
    ]
    try:
        resp = call_openai_with_retry(model=model, content_payload=content)
        return (getattr(resp, "output_text", None) or "").strip()
    except TypeError:
        # 이미지 입력 미지원 폴백(차선) — 텍스트만으로라도 요약 생성
        log("[WARN] TypeError in vision call. Falling back to text-only summary.")
        try:
            time.sleep(REQUEST_INTERVAL_SEC)
            chat = client.chat.completions.create(
                model=model,
                messages=[
                    {"role":"system","content":SYSTEM_PROMPT_VISUAL},
                    {"role":"user","content":f"{prompt_text}\n\n[참고: 이미지 입력 폴백 경로, 텍스트 기준 요약을 생성하세요.]"}
                ]
            )
            return (chat.choices[0].message.content or "").strip()
        except Exception as e:
            log(f"[ERROR] Fallback also failed: {e}")
            return ""

# ======================== 4) 페이지 단위 요약 ========================
def summarize_pages(image_paths: List[str]) -> Dict[str, str]:
    start_time = 0
    cp = load_checkpoint()       # { "p1": "...", "p2": "...", ... }
    total = len(image_paths)
    updated = False
    
    for i, img in enumerate(image_paths, start=2):
        elapsed = time.time() - start_time  # start_time을 함수 시작부에 추가
        log(f"▶ [{i}/{total}] 진행률: {i/total*100:.1f}% | 경과: {elapsed:.0f}초")
        key = f"p{i}"
        # 현재 이미지/프롬프트 시그니처 준비
        img_sha = sha256_file(img)
        ah = average_hash(img)
        p_prompt = page_summary_prompt(i, total, LANG)
        p_sig = prompt_signature(p_prompt)
        
        # 건너뛰기 판정
        cached = cp.get(key)
        skip = False
        if isinstance(cached, str):
            cp[key] = {"md": cached}
            cached = cp[key]
            save_checkpoint(cp)
            
        # ✅ 안전한 비교 (dict일 때만 비교)
        if isinstance(cached, dict):
            if (cached.get("img_sha") == img_sha and
                cached.get("ahash") == ah and
                cached.get("prompt_sig") == p_sig and
                cached.get("sys_prompt_sig") == SYSTEM_PROMPT_SIG and   # ✅ 시스템 프롬프트 해시도 비교
                cached.get("model") == MODEL_VISION):
                skip = True

        if skip:
            log(f"▶ 페이지 요약 건너뜀(체크포인트 hit): {human_page(i,total)}")
            continue
        # 비용 절감: 빈(또는 거의 빈) 슬라이드 감지 시 초소형 요약만 요청하거나 스킵 옵션
        if image_is_mostly_blank(img):
            log(f"⚠ 빈/저대비 슬라이드 감지: {human_page(i,total)} → 간단 요약 시도")
            p_prompt += "\n\n[추가 규칙] 이 페이지는 빈/저대비 슬라이드로 감지됨. 제목/메타만 간단 기록하고 상세는 생략."
        
        log(f"▶ 페이지 요약 요청: {human_page(i,total)}")
        out = gpt_vision_on_image(p_prompt, img, model=MODEL_VISION)
        out = sanitize_page_md(out)

        cp[key] = {
            "md": out,
            "img_sha": img_sha,
            "ahash": ah,
            "prompt_sig": p_sig,
            "sys_prompt_sig": SYSTEM_PROMPT_SIG,
            "model": MODEL_VISION
        }
        updated = True
        # 매 페이지마다 저장
        save_checkpoint(cp)
        
    if not updated:
        log("ℹ 체크포인트 일치: 변경된 페이지가 없어 새 호출 없음")
    return {k: v["md"] if isinstance(v, dict) and "md" in v else v for k, v in cp.items() if k.startswith("p")}

# ======================== 5) 통합 프롬프트(요약/빈칸/퀴즈) ========================
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

def prompt_aggregate_summary(all_pages_md: str) -> str:
    return (
        SYSTEM_PROMPT_VISUAL + "\n\n" + 
        AGG_PROMPT_BASE +
        "\n[요청]\n"
        "아래 페이지 요약을 바탕으로 **요약 노트(JSON)** 한 개 객체로만 출력하라. 스키마는 다음과 같다:\n"
        "{\n"
        '  "meta": { "title": "string", "course": "string", "date": "string", "language": "ko" },\n'
        '  "style": { "section_rule": true, "heading_spacing_after": "1-line", "tables": {"header_color":"#EAF3FF","zebra_stripe":true}, "layout":{"avoid_manual_pagebreaks":true,"compact":true} },\n'
        '  "summaries": {\n'
        '    "standard": {\n'
        '        "sections": [ {\n' 
        '            "h2":"string",\n' 
        '            "paragraphs":["..."],\n' 
        '            "bullets":["..."],\n' 
        '            "tables":[{"title":"string","columns":["..."],"rows":[["..."]]}]\n' 
        '         } ],\n'
        '       "glossary:[["용어","설명"]],\n'
        '       "checklist":["..."]\n'
        '   }\n'
        "  },\n"
        '  "highlight_pages": [] # 실제 중요 페이지 번호\n'
        "}\n"
        "- 최종 산출물은 반드시 한국어(KO)로 작성하라.\n"
        "- 과도한 중복 제거, 수식은 $...$ 유지, 기술 용어 영어 유지.\n"
        "\n[입력 원본(페이지 요약)]\n" + all_pages_md
    )

def prompt_aggregate_blank(all_pages_md: str, min_clozes: int) -> str:
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
        "\n[입력 원본(페이지 요약)]\n" + all_pages_md
    )

def prompt_aggregate_quiz(
    all_pages_md: str,
    min_clozes: int,
    allow_short_answer: bool
) -> str:
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
            "  - 예: 용어 이름, 기법 이름, 구성 요소 이름, 1개의 수식 이름 등.\n"
            "  - **설명형 문장(예: '~을 의미한다', '~하는 기법이다')을 a에 쓰지 말 것.**\n"
            "  - a는 가능하면 명사/명사구 형태로만 작성하라.\n"
            "- short_answer의 q는\n"
            "  - \"~을 무엇이라고 하나요?\", \"~를 가리키는 용어는?\", \"~의 이름은?\"과 같이\n"
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
            f"- 최소 {min_clozes}문항 이상 출제하고, "
            "**단답형(short_answer)은 만들지 말 것. 오직 multiple_choice만 생성**하라.\n"
        )

    common_rules = (
        "- 각 문항은 강의 내용만을 기반으로 하고, 페이지 요약에서 중요하게 표시된 개념을 우선적으로 묻는다.\n"
        "- multiple_choice의 보기(options)는 서로 충분히 헷갈릴 수 있도록 구성하되, 명백히 틀린 선택지는 넣지 않는다.\n"
        "- 모든 텍스트는 한국어로 작성하라.\n"
        "- 최종 산출물은 반드시 유효한 JSON 하나만 출력하고, 마크다운/코드블록/설명 문장은 넣지 말 것.\n"
        "\n[입력 원본(페이지 요약)]\n"
    )

    return base + schema + common_rules + all_pages_md



# ======================== 6) 통합 LLM 호출(JSON 강제) ========================
def call_llm_on_text(
    text_prompt: str,
    system_prompt: str = SYSTEM_PROMPT_VISUAL,
    *,
    max_output_tokens: int = 5000,
    temperature: float = 0.2,
    top_p: float = 0.9,
    min_sections: int = 6,
    min_glossary: int = 12,
    min_checklist: int = 10,
    retries: int = 1,
) -> dict:
    def _make_messages(extra_hint: str = ""):
        sys_content = [{"type": "input_text", "text": (system_prompt or "").strip()}]
        user_text = text_prompt if not extra_hint else (text_prompt + "\n\n" + extra_hint)

        user_content = [{"type": "input_text", "text": user_text}]
        # pdf는 이미지도 같이 보낼 거면 여기서 append
        # for p in page_images[:MAX_IMAGES_PER_CALL]:
        #     user_content.append({"type":"input_image","image_url":...})

        return [
            {"role": "system", "content": sys_content},
            {"role": "user", "content": user_content},
        ]

    def _extract_text(resp) -> str:
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
            return True

    # 1차 호출
    messages = _make_messages()
    resp = client.responses.create(
        model=MODEL_VISION,
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

    # 분량 부족하면 1회 보강
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
            model=MODEL_VISION,
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

        if not isinstance(obj, dict) or _is_poor(obj):
            obj = obj2

    return obj

# ======================== 7) 파싱/보정 유틸(JSON) ========================
def _strip_code_fences(s: str) -> str:
    # ```...``` 블록을 전부 제거
    return re.sub(r"```(?:[\s\S]*?)```", "", s).strip()

def _json_block_to_md(s: str) -> Optional[str]:
    """
    ```json ... ``` 또는 맨바닥 JSON이 들어오면 sections[].h2/paragraphs/bullets를 마크다운으로 변환.
    """
    # 코드펜스 내부 JSON 추출
    m = re.search(r"```json\s+([\s\S]*?)\s+```", s, flags=re.I)
    raw = None
    if m:
        raw = m.group(1)
    else:
        # 맨바닥 JSON일 수도 있음
        js = extract_json_object(s)
        if js is not None:
            raw = json.dumps(js, ensure_ascii=False)

    if not raw:
        return None

    try:
        obj = json.loads(raw)
    except Exception:
        # 간단 복구 시도
        obj = _json_autofix(raw)

    if not isinstance(obj, dict):
        return None

    # 흔한 구조 가정: {sections:[{h2, paragraphs, bullets}]}
    sections = []
    # 1) straight
    cand = obj.get("sections")
    # 2) KHUNote 스타일
    if cand is None:
        cand = obj.get("summaries", {}).get("standard", {}).get("sections")

    if isinstance(cand, list):
        for i, sec in enumerate(cand, start=1):
            h2 = (sec.get("h2") or f"Section {i}").strip()
            pars = [p for p in (sec.get("paragraphs") or []) if isinstance(p, str)]
            bulls = [b for b in (sec.get("bullets") or []) if isinstance(b, str)]
            buf = [f"### {h2}"]
            for p in pars:
                buf.append(p)
            for b in bulls:
                buf.append(f"• {b}")
            sections.append("\n".join(buf).strip())

    if not sections:
        return None
    return "\n\n".join(sections).strip()

def save_page_summaries_json(
    page_summaries: Dict[str, str],
    image_paths: List[str],
    checkpoint_path: str,
    out_path: str
) -> None:
    """
    summarize_pages()가 반환한 page_summaries와 checkpoint 메타를 묶어
    페이지 단위 JSON으로 저장.
    """
    # 체크포인트(해시, 프롬프트 시그니처 등)를 합쳐서 풍부한 메타를 만든다
    cp = {}
    try:
        if os.path.exists(checkpoint_path):
            with open(checkpoint_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
                # 이전 버전 호환: 문자열만 저장된 경우 md 키로 감싼다
                for k, v in raw.items():
                    if isinstance(v, str):
                        cp[k] = {"md": v}
                    else:
                        cp[k] = v or {}
    except Exception as e:
        log(f"[WARN] checkpoint 읽기 실패: {e}")

    total = len(image_paths)
    records = []
    for idx in range(1, total + 1):
        key = f"p{idx}"
        md = page_summaries.get(key, "")
        meta = cp.get(key, {})
        rec = {
            "page": idx,
            "summary_md": md,
            "image_path": image_paths[idx - 1] if 0 <= idx - 1 < len(image_paths) else None,
            # 체크포인트에 있으면 메타도 함께 저장 (없으면 None)
            "img_sha": meta.get("img_sha"),
            "ahash": meta.get("ahash"),
            "prompt_sig": meta.get("prompt_sig"),
            "sys_prompt_sig": meta.get("sys_prompt_sig"),
            "model": meta.get("model"),
        }
        records.append(rec)

    payload = {
        "meta": {
            "source_pdf": os.path.abspath(PDF_FILE),
            "total_pages": total,
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "language": LANG,
            "model": MODEL_VISION,
        },
        "pages": records,
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    log(f"✅ 페이지별 요약 JSON 저장: {out_path}")

def sanitize_page_md(s: str) -> str:
    """
    1) ```json ...```이 있으면 마크다운으로 변환
    2) 그 외의 코드펜스는 제거
    """
    md_from_json = _json_block_to_md(s)
    if md_from_json:
        return md_from_json
    return _strip_code_fences(s)

def _pages_for_section(sec: dict, highlight_pool: list) -> list:
    # 1) 섹션이 직접 pages를 갖고 있으면 그걸 사용
    if isinstance(sec.get("pages"), list) and sec["pages"]:
        return [p for p in sec["pages"] if isinstance(p, int)]
    # 2) images 안에 page 지정이 있으면 사용
    imgs = sec.get("images") or []
    for it in imgs:
        if isinstance(it, dict) and isinstance(it.get("page"), int):
            return [it["page"]]
    # 3) 마지막 수단: highlight_pages 풀에서 하나씩 꺼내서 매칭
    if highlight_pool:
        return [highlight_pool.pop(0)]
    return []

def parse_highlight_pages(llm_output: str, total_pages: int) -> List[int]:
    """
    LLM 출력 마지막/별도 줄의 {"highlight_pages":[...]} JSON을 찾아 페이지 배열을 반환.
    범위를 벗어난 번호는 제거.
    """
    matches = re.findall(r'\{\s*"highlight_pages"\s*:\s*\[(.*?)\]\s*\}', llm_output, flags=re.S)
    if not matches: return []
    nums = re.findall(r'\d+', matches[-1])  # 마지막 매치 사용
    pages = sorted({int(n) for n in nums if 1 <= int(n) <= total_pages})
    with open(HIGHLIGHT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump({"highlight_pages": pages}, f, ensure_ascii=False, indent=2)
    return pages


def extract_json_object(text: str) -> Optional[dict]:
    """
    모델이 앞뒤로 잡담을 붙이지 않도록 유도했지만,
    혹시 몰라서 첫 번째 JSON 객체를 추출해 파싱한다.
    """
    # 가장 앞의 '{'부터 끝 '}'까지 근사 추출
    start = text.find('{')
    end = text.rfind('}')
    if start == -1 or end == -1 or end <= start:
        return None
    candidate = text[start:end+1]
    try:
        return json.loads(candidate)
    except Exception:
        # 백업: 큰따옴표 누락/문법오류 등은 원문 저장 쪽으로 fallback
        return None

def _json_autofix(s: str) -> Optional[dict]:
    """
    작은따옴표→큰따옴표, 트레일링 콤마 제거 등 경미한 오류 자동 복구 시도도
    """
    t = s.strip()
    # 1) 코드블럭/마크다운 제거
    if t.startswith("```"):
        t = re.sub(r"^```(json)?\s*|\s*```$", "", t, flags=re.S)

    # 2) 가장 바깥 JSON만 추출
    start, end = t.find("{"), t.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    t = t[start:end+1]

    # 3) 홑따옴표를 큰따옴표로(키/문자열에 한정) — 안전하지 않아 최소 치환
    #   키: 'key': → "key":
    t = re.sub(r"\'([A-Za-z0-9_\-]+)\'\s*:", r'"\1":', t)
    #   값 문자열: : 'text' → : "text"
    t = re.sub(r':\s*\'([^\'\\]*)\'', r': "\1"', t)

    # 4) 트레일링 콤마 제거 → }, ], ,} ,]
    t = re.sub(r",\s*([\}\]])", r"\1", t)

    try:
        return json.loads(t)
    except Exception:
        return None

def _nonempty_tier(t: dict) -> bool:
    """
    요약 티어 객체에 유효한 섹션이 포함되어 있는지 확인
    """
    return bool(t) and isinstance(t.get("sections", []), list) and len(t["sections"]) > 0

# 스키마 기본값 보정기
def _fill_summary_defaults(obj: dict, lang: str = "ko") -> dict:
    if "meta" not in obj: obj["meta"] = {}
    obj["meta"].setdefault("title", "Lecture Summary")
    obj["meta"].setdefault("course", "")
    obj["meta"].setdefault("date", time.strftime("%Y-%m-%d"))
    obj["meta"].setdefault("language", lang)

    if "style" not in obj: obj["style"] = {}
    style = obj["style"]
    style.setdefault("section_rule", True)
    style.setdefault("heading_spacing_after", "1-line")
    style.setdefault("tables", {"header_color":"#EAF3FF","zebra_stripe":True})
    style.setdefault("layout", {"avoid_manual_pagebreaks":True,"compact":True})

    if "summaries" not in obj: obj["summaries"] = {}
    for tier in ("short","standard","detailed"):
        obj["summaries"].setdefault(tier, {})
        t = obj["summaries"][tier]
        t.setdefault("sections", [])
        t.setdefault("glossary", [])
        t.setdefault("checklist", [])
        # 섹션 안전 필터
        fixed_sections = []
        for sec in t["sections"]:
            if not isinstance(sec, dict): continue
            sec.setdefault("h2","")
            sec.setdefault("paragraphs", [])
            sec.setdefault("bullets", [])
            sec.setdefault("tables", [])
            sec.setdefault("images", [])
            fixed_sections.append(sec)
        t["sections"] = fixed_sections

    obj.setdefault("references", [])
    obj.setdefault("highlight_pages", [])
    
    standard_sections = obj["summaries"]["standard"].get("sections")
    short_sections = obj["summaries"]["short"].get("sections")
    detailed_sections = obj["summaries"]["detailed"].get("sections")

    # 표준 티어(standard)가 비어 있을 경우, short나 detailed에서 내용을 복사해 기본 본문을 보장
    if not standard_sections:
        if short_sections:
            obj["summaries"]["standard"]["sections"] = short_sections
        elif detailed_sections:
            obj["summaries"]["standard"]["sections"] = detailed_sections
    
    return obj

# ======================== 8) PDF 렌더러 (JSON/Markdown) ========================
def export_pdf_from_json(data: dict, outpath: str, image_paths_map: Optional[ImagePaths] = None): # 🚨 [수정 2] image_paths_map 인자 추가

    doc = SimpleDocTemplate(
        outpath, pagesize=A4,
        leftMargin=16*mm, rightMargin=16*mm,
        topMargin=16*mm, bottomMargin=16*mm
    )
    styles = getSampleStyleSheet()
    # 한글 본문 스타일
    styles.add(ParagraphStyle(name="BodyKR", parent=styles["Normal"], fontName="HYSMyeongJo-Medium", fontSize=10, leading=14))
    styles.add(ParagraphStyle(name="H2KR", parent=styles["Heading2"], fontName="HYSMyeongJo-Medium", spaceAfter=6))
    styles.add(ParagraphStyle(name="SmallGrey", parent=styles["Normal"], fontName="HYSMyeongJo-Medium", fontSize=8, textColor=colors.grey))
    # 🚨 [추가 3] 하이라이트 섹션 스타일
    styles.add(ParagraphStyle(name="HighlightHeading", parent=styles["Normal"], fontName="HYSMyeongJo-Medium", fontSize=10, textColor=colors.HexColor("#0070C0"), spaceAfter=1*mm))
    styles.add(ParagraphStyle(name="HighlightPage", parent=styles["Normal"], fontName="HYSMyeongJo-Medium", fontSize=8, textColor=colors.grey, spaceBefore=0, spaceAfter=2*mm))

    story = []

    meta = data.get("meta", {})
    title = meta.get("title", "Lecture Summary")
    course = meta.get("course", "")
    date = meta.get("date", "")

    story.append(Paragraph(title, styles["Heading1"]))
    sub = " · ".join([x for x in [course, date] if x])
    if sub:
        story.append(Paragraph(sub, styles["SmallGrey"]))
    story.append(Spacer(1, 6*mm))

    style_cfg = data.get("style", {})
    rule_on = style_cfg.get("section_rule", True)
    table_cfg = data.get("style", {}).get("tables", {"header_color":"#EAF3FF","zebra_stripe":True}) # 테이블 설정 다시 읽기
    
    # 🚨 [추가 4] 썸네일 설정을 PDF에 반영
    include_images = PDF_INCLUDE_IMAGES and image_paths_map and image_paths_map.page_to_path
    temp_files_to_clean = []
    def section_rule():
        # 얇은 구분선
        tbl = Table([[""]], colWidths=[doc.width])
        tbl.setStyle(TableStyle([
            ("LINEBELOW", (0,0), (-1,-1), 0.5, colors.HexColor("#DDDDDD")),
            ("LEFTPADDING",(0,0),(-1,-1),0), ("RIGHTPADDING",(0,0),(-1,-1),0),
            ("TOPPADDING",(0,0),(-1,-1),2), ("BOTTOMPADDING",(0,0),(-1,-1),6),
        ]))
        return tbl

    def bullets_flow(items: list):
        # 간단 불릿 렌더(두 레벨까지만)
        flows = []
        for it in items:
            flows.append(Paragraph(f"• {it}", styles["BodyKR"]))
        return flows

    def table_from_spec(spec: dict):
        title = spec.get("title")
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
            ("GRID", (0,0), (-1,-1), 0.25, colors.HexColor("#CCCCCC")),
        ]
        if table_cfg.get("zebra_stripe", True):
            for r in range(1, len(data_tbl)):
                if r % 2 == 1:
                    ts.append(("BACKGROUND", (0,r), (-1,r), colors.whitesmoke))
        t.setStyle(TableStyle(ts))
        flows = []
        if title:
            flows.append(Paragraph(title, styles["SmallGrey"]))
        flows.append(t)
        return flows
    
        # --- 섹션에 매칭할 페이지 번호 선택 ---
    def _pages_for_section(sec: dict, highlight_pool: list) -> list:
        # 1) 섹션에 pages가 명시돼 있으면 우선 사용
        if isinstance(sec.get("pages"), list) and sec["pages"]:
            return [p for p in sec["pages"] if isinstance(p, int)]
        # 2) images에 page가 명시돼 있으면 그 중 첫 번째 사용
        imgs = sec.get("images") or []
        for it in imgs:
            if isinstance(it, dict) and isinstance(it.get("page"), int):
                return [it["page"]]
        # 3) 아무 힌트도 없으면 highlight_pages 풀에서 하나씩 소비
        if highlight_pool:
            return [highlight_pool.pop(0)]
        return []
    
        # --- 섹션 바로 뒤에 썸네일 Flowable 삽입 (테이블 X) ---
    def _append_section_thumbnail(story, page_nums, image_paths_map, styles,
                                  max_w_mm=70, max_h_mm=60):
        if not page_nums or not image_paths_map or not image_paths_map.page_to_path:
            return []
        temp_files = []
        for p in page_nums:
            img_path = image_paths_map.page_to_path.get(p)
            if not img_path or not os.path.exists(img_path):
                continue
            try:
                with PILImage.open(img_path) as pil:
                    w, h = pil.size or (1, 1)
                    aspect = h / float(w) if w else 1.0
                    target_w = max_w_mm * mm
                    target_h = max_h_mm * mm
                    draw_w = target_w
                    draw_h = target_w * aspect
                    if draw_h > target_h:
                        draw_h = target_h
                        draw_w = target_h / aspect

                    # ReportLab 안정성 위해 임시 PNG 생성
                    tmp = os.path.join(WORKDIR, f"sec_thumb_p{p}_{time.time()}.png")
                    pil.resize(
                        (int(draw_w/mm * DPI / 25.4), int(draw_h/mm * DPI / 25.4)),
                        PILImage.LANCZOS
                    ).convert("RGB").save(tmp, "PNG")
                    temp_files.append(tmp)

                story.append(Spacer(1, 2*mm))
                story.append(Paragraph(f"슬라이드 미니뷰 (p.{p})", styles["SmallGrey"]))
                story.append(FixedImage(tmp, width=draw_w, height=draw_h))
                story.append(Spacer(1, 4*mm))
            except Exception as e:
                log(f"[WARN] 섹션 썸네일 렌더 실패 p.{p}: {e}")
        return temp_files
    
    # [추가 5] 썸네일 렌더링 함수
    def render_highlight_thumbnails(highlight_pages: List[int]):
        THUMBNAIL_WIDTH_MM = 50 * mm # 썸네일 너비 50mm
        MAX_THUMB_H = 60 * mm
        
        # 페이지 번호별 이미지 경로가 없는 경우 리턴
        if not image_paths_map or not image_paths_map.page_to_path:
            return

        story.append(Spacer(1, 4*mm))
        story.append(Paragraph("📌 AI가 선정한 핵심 페이지", styles["HighlightHeading"]))
        
        # 썸네일 배치를 위한 테이블 정의
        MAX_COLS = 3  # 한 줄에 최대 3개 배치
        current_row = []
        col_widths = [doc.width / MAX_COLS] * MAX_COLS
        table_data = []
        
        temp_files = []

        for page_num in highlight_pages:
            img_path = image_paths_map.page_to_path.get(page_num)
            
            if img_path and os.path.exists(img_path):
                temp_png_path = None
                try:
                    # 1. PIL로 이미지 열기 및 크기 계산
                    # with Image.open(img_path) as img_pil: # 원본 이미지 열기
                    # Note: JPEG 메타데이터 오류 회피를 위해, 파일을 직접 읽지 않고 
                    # 렌더링에 필요한 PIL 리사이즈 및 PNG 변환을 수행
                    with PILImage.open(img_path) as img_pil:
                        original_width, original_height = img_pil.size
                        aspect_ratio = original_height / original_width
                        thumb_height = min(MAX_THUMB_H, THUMBNAIL_WIDTH_MM * aspect_ratio) 
                        
                        thumb_width_px = int(THUMBNAIL_WIDTH_MM / mm * DPI / 25.4) # mm -> pixel (DPI 150 기준)
                        # PIL 리사이즈. PIL 객체는 반드시 RGB여야 ReportLab에서 오류가 적음.
                        img_resized = img_pil.resize((thumb_width_px, int(thumb_width_px * aspect_ratio)), PILImage.LANCZOS).convert("RGB")
                        # ReportLab Image에 전달할 JPEG 데이터 준비 (메모리 버퍼 사용)


                        temp_png_path = os.path.join(WORKDIR, f"temp_thumb_{page_num}_{time.time()}.png")
                        img_resized.save(temp_png_path, format="PNG")
                        temp_files.append(temp_png_path)
                        
                        # kind='absolute'는 ReportLab에게 크기 계산을 하지 말고 명시된 width/height를 사용하도록 강제
                        rl_img = FixedImage(temp_png_path, width=THUMBNAIL_WIDTH_MM, height=thumb_height)
                        
                        # 이미지 아래에 페이지 번호 추가
                        caption = Paragraph(f"[P. {page_num}]", styles["HighlightPage"])
                        
                        MAX_CELL_H = 70 * mm
                        cell_box = KeepInFrame(col_widths[0], MAX_CELL_H, content=[rl_img, caption], mode="shrink")
                        current_row.append(cell_box)
    
                        # 현재 행이 꽉 찼으면 테이블 데이터에 추가하고 새 행 시작
                        if len(current_row) == MAX_COLS:
                            table_data.append(current_row)
                            current_row = []
                except Exception as e:
                    # 파일 읽기 또는 ReportLab 객체 생성 시 오류 발생 시 건너뛰고 경고
                    log(f"[WARN] 썸네일 렌더링 실패 (P.{page_num}): {e}")
                    pass

        # 마지막 남은 행 추가
        if current_row:
            # 남은 셀을 빈 문자열로 채워 테이블 구조 유지
            while len(current_row) < MAX_COLS:
                current_row.append("")
            table_data.append(current_row)

        if table_data:
            thumb_table = Table(table_data, colWidths=col_widths, hAlign='LEFT')
            # 썸네일 테이블 스타일
            thumb_table.setStyle(TableStyle([
                ('LEFTPADDING', (0,0), (-1,-1), 2),
                ('RIGHTPADDING', (0,0), (-1,-1), 6), # 오른쪽 간격
                ('TOPPADDING', (0,0), (-1,-1), 2),
                ('BOTTOMPADDING', (0,0), (-1,-1), 6), # 아래 간격
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ]))
            story.append(thumb_table)
            story.append(section_rule())
            story.append(Spacer(1, 4*mm))
        return temp_files

    # 어떤 티어를 PDF로 쓸지 선택 (예: standard 우선, 없으면 detailed→short)
    summaries = data.get("summaries", {})
    tier = None
    
    for cand in ("detailed", "standard", "short"):
        t = summaries.get(cand)
        if _nonempty_tier(t):
            tier = t
            break
    if tier is None:
        tier = {"sections": []}
    
    highlight_pool = list(data.get("highlight_pages", []))
        
    for sec in tier.get("sections", []):
        h = sec.get("h2", "").strip() or "Untitled"
        paragraphs = sec.get("paragraphs", [])
        bullets = sec.get("bullets", [])
        tables = sec.get("tables", [])

        block = []
        block.append(Paragraph(h, styles["H2KR"]))
        if rule_on:
            block.append(section_rule())

        for p in paragraphs:
            block.append(Paragraph(p, styles["BodyKR"]))
            block.append(Spacer(1, 1*mm))

        for b in bullets_flow(bullets):
            block.append(b)

        for tspec in tables:
            block.extend(table_from_spec(tspec))
            block.append(Spacer(1, 2*mm))

        story.append(KeepTogether(block))
        story.append(Spacer(1, 4*mm))
        section_pages = _pages_for_section(sec, highlight_pool)
        temp_files_to_clean.extend(
            _append_section_thumbnail(story, section_pages, image_paths_map, styles)
        )

    # Glossary 렌더링 (Blank 모드 데이터 보존)
    glossary = data.get("glossary", [])
    if glossary and MODE == "summary":
        story.append(PageBreak())
        story.append(Paragraph("용어 정리 (Glossary)", styles["H2KR"]))
        story.append(section_rule())
        
        # 용어집은 2열 테이블로 렌더링
        glossary_table = Table([[Paragraph(c, styles["BodyKR"]) for c in row] for row in glossary], colWidths=[doc.width * 0.3, doc.width * 0.7], hAlign='LEFT')
        glossary_table.setStyle(TableStyle([
            ('FONTNAME', (0,0), (-1,-1), 'HYSMyeongJo-Medium'),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('GRID', (0,0), (-1,-1), 0.25, colors.HexColor("#DDDDDD")),
            ('LEFTPADDING', (0,0), (-1,-1), 4),
            ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(glossary_table)
        story.append(Spacer(1, 4*mm))

    checklist = data.get("checklist", [])
    if checklist and MODE == "summary":
        story.append(PageBreak())
        story.append(Paragraph("확인 목록 (Checklist)", styles["H2KR"]))
        story.append(section_rule())
        
        # 체크리스트는 번호 없는 목록으로 렌더링
        for item in checklist:
            # ⬜ 유니코드를 사용하여 체크박스처럼 보이게 함
            story.append(Paragraph(f"⬜ {item}", styles["BodyKR"]))
            story.append(Spacer(1, 1*mm))
        story.append(Spacer(1, 4*mm))

    answer_sheet = data.get("answer_sheet", None)
    if answer_sheet and isinstance(answer_sheet, dict):
        items = answer_sheet.get("items", [])
        if items:
            ans_title = answer_sheet.get("title", "정답 모음")
            story.append(PageBreak())
            story.append(Paragraph(ans_title, styles["H2KR"]))
            if rule_on:
                story.append(section_rule())
            for it in items:
                story.append(Paragraph(it, styles["BodyKR"]))

    doc.build(story)
    return temp_files_to_clean

# ======================== 메인 ========================
def main():
    if not os.path.exists(PDF_FILE):
        raise FileNotFoundError(f"PDF 파일을 찾을 수 없습니다: {PDF_FILE}")

    current_pdf_hash = sha256_file(PDF_FILE)
    last_hash = read_text(INPUT_HASH_PATH).strip()

    if last_hash and last_hash != current_pdf_hash:
        log("ℹ 입력 PDF가 변경됨을 감지 → 체크포인트/페이지 캐시 초기화")
        # 체크포인트 삭제
        try:
            if os.path.exists(CHECKPOINT_PATH):
                os.remove(CHECKPOINT_PATH)
        except Exception as e:
            log(f"[WARN] 체크포인트 삭제 실패: {e}")

        # pages 폴더 비우기
        try:
            import glob
            for f in glob.glob(os.path.join(WORKDIR, "pages", "page_*.jpg")):
                os.remove(f)
        except Exception as e:
            log(f"[WARN] pages 정리 실패: {e}")

    # 현재 해시 저장(다음 실행 대비)
    write_text(INPUT_HASH_PATH, current_pdf_hash)

    # 1) PDF → 이미지
    img_dir = os.path.join(WORKDIR, "pages")
    if ALWAYS_CLEAN_PAGES:
        try:
            import glob
            for f in glob.glob(os.path.join(img_dir, "page_*.jpg")):
                os.remove(f)
        except Exception as e:
            log(f"[WARN] ALWAYS_CLEAN_PAGES 정리 실패: {e}")
    image_paths = pdf_to_images(PDF_FILE, img_dir, dpi=DPI, poppler_path=POPPLER_PATH)
    
    # 이미지 경로 맵 생성 (썸네일 삽입을 위함)
    page_to_path_map = {i + 1: path for i, path in enumerate(image_paths)}
    img_path_manager = ImagePaths(page_to_path_map)

    # 2) 페이지 단위 요약(체크포인트 지원)
    page_summaries = summarize_pages(image_paths)  # { "p1":"...", ... }
    total = len(image_paths)

    # 3) 통합요청
    #   페이지 순서대로 합치기
    ordered_md = []
    for i in range(1, total+1):
        k = f"p{i}"
        if k in page_summaries:
            ordered_md.append(sanitize_page_md(page_summaries[k]))
    all_pages_md = "\n\n".join(ordered_md)
    
    try:
        save_page_summaries_json(
            page_summaries=page_summaries,
            image_paths=image_paths,
            checkpoint_path=CHECKPOINT_PATH,
            out_path=PAGE_SUMMARIES_JSON_PATH
        )
    except Exception as e:
        log(f"[WARN] 페이지별 요약 JSON 저장 실패: {e}")
    
    # 🚨 [추가] 통합 프롬프트 크기 경고
    try:
        prompt_bytes = all_pages_md.encode('utf-8')
        if len(prompt_bytes) > MAX_AGGREGATE_PROMPT_BYTES:
            log(f"⚠️ [WARNING] 통합 프롬프트 크기가 {len(prompt_bytes)/1024:.0f}KB로 과도하게 큽니다. (제한: {MAX_AGGREGATE_PROMPT_BYTES/1024:.0f}KB)")
            log("이는 LLM API 호출 실패, 속도 저하, 또는 비용 증가를 유발할 수 있습니다. 입력 PDF를 분할하는 것을 고려하세요.")
    except Exception:
        pass # 인코딩 실패 시 무시

    if MODE == "summary":
        log("▶ 통합 요약(JSON) 생성")
        data = call_llm_on_text(prompt_aggregate_summary(all_pages_md), system_prompt=SYSTEM_PROMPT_VISUAL)
        raw_output_path = SUMMARY_JSON_PATH.replace(".json", "_raw_llm_output.txt")
        write_text(raw_output_path, json.dumps(data, ensure_ascii=False, indent=2))
        log(f"ℹ LLM 원시 출력 저장 (디버깅용): {raw_output_path}")

        if not isinstance(data, dict):
            log("[ERROR] LLM 결과가 dict가 아닙니다. _fill_summary_defaults 호출 불가.")
            data = {"raw_output_invalid_type": str(data)}

        # 스키마 기본값 채우기(견고성)
        data = _fill_summary_defaults(data, lang=LANG)
        
        summaries = data.get("summaries", {})
        tier_names = ["standard", "detailed", "short"]
        selected_tier = None
        for cand in tier_names:
            t = summaries.get(cand)
            if _nonempty_tier(t):
                selected_tier = cand
                break
        
        if selected_tier:
             log(f"ℹ PDF 렌더링에 사용될 티어: {selected_tier}. 섹션 수: {len(data['summaries'][selected_tier]['sections'])}")
        else:
             log("[WARN] PDF 렌더링에 사용할 유효한 요약 섹션(standard/detailed/short)을 찾지 못했습니다.")
        
        try:
            hps = data.get("highlight_pages", [])
            if isinstance(hps, list):
                with open(HIGHLIGHT_JSON_PATH, "w", encoding="utf-8") as f:
                    json.dump({"highlight_pages": hps}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            log(f"[WARN] highlight_pages 저장 실패: {e}")

        with open(SUMMARY_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        log(f"✅ 요약 JSON 저장: {SUMMARY_JSON_PATH}")
        
        temp_files_to_clean = [] # 정리할 임시 파일 리스트 초기화
        try:
            # 2) ✅ JSON → PDF 변환 호출 및 임시 파일 목록 받기
            temp_files_to_clean = export_pdf_from_json(data, SUMMARY_PDF_PATH, image_paths_map=img_path_manager) # 🚨 반환 값 받기
            log(f"✅ 요약 PDF 저장: {SUMMARY_PDF_PATH}")
        finally:
            # 🚨 [핵심 수정]: PDF 생성이 완료된 후 임시 파일 정리
            for f in temp_files_to_clean:
                try:
                    os.remove(f)
                    log(f"ℹ 임시 파일 정리: {os.path.basename(f)}")
                except Exception as e:
                    log(f"[WARN] 임시 파일 정리 실패: {os.path.basename(f)}, {e}")
            if temp_files_to_clean:
                log(f"ℹ 총 {len(temp_files_to_clean)}개 임시 파일 정리 완료.")

    elif MODE == "blank":
        log("▶ 빈칸 채우기 노트(JSON) 생성")
        min_clozes = round(total / 3)
        data = call_llm_on_text(prompt_aggregate_blank(all_pages_md, min_clozes), system_prompt=SYSTEM_PROMPT_VISUAL)
        raw_output_path = BLANK_JSON_PATH.replace(".json", "_raw_llm_output.txt") # 🚨 [추가] 원시 출력 저장
        write_text(raw_output_path, json.dumps(data, ensure_ascii=False, indent=2))
        log(f"ℹ LLM 원시 출력 저장 (디버깅용): {raw_output_path}")

        
        if not data:
            log("[ERROR] JSON 파싱/복구 최종 실패. 원시 출력 확인 필요.")
            data = {"raw_output_could_not_be_parsed": data}

        data = _fill_summary_defaults(data, lang=LANG) 

        print(data)
        clozes = data.get("clozes", [])
        if not clozes:
             log("⚠️ [WARNING] LLM이 'clozes' 목록을 생성하지 않았습니다. PDF에 빈칸 문제가 없습니다.")
             log(f"💡 LLM 출력 파일({os.path.basename(raw_output_path)})을 확인하여 clozes 필드 누락 원인을 파악하세요.")
        # 본문: 정답 숨김
        bullets = [c.get("text", "") for c in clozes]
        # 마지막 장 정답 모음
        answers = [f"{i+1}. {c.get('answer','')}" for i, c in enumerate(clozes)]
        
        standard_summaries = data.get("summaries", {}).get("standard", {})
        glossary = []
        checklist = []

        mapped = {
            "meta": {"title":"빈칸 채우기 노트 (정답 숨김)","course":"","date":time.strftime("%Y-%m-%d"),"language":LANG},
            "style": {"section_rule": True, "tables":{"header_color":"#EAF3FF","zebra_stripe":True}},
            "summaries": {
                "standard": {
                    "sections": [{
                        "h2": "Fill-in-the-Blank",
                        "paragraphs": [
                            "빈칸(____)에 들어갈 핵심 용어/숫자/기호를 채우세요.",
                            "정답은 문서 맨 마지막 '정답 모음' 페이지에 있습니다."
                        ],
                        "bullets": bullets
                    }],

                }
            },
            "highlight_pages": [],
            # ✅ 정답 모음은 렌더러에서 마지막 페이지로 출력
            "answer_sheet": {
                "title": "정답 모음",
                "items": answers
            }
        }
        
        temp_files_to_clean = [] # 정리할 임시 파일 리스트 초기화
        try:
            temp_files_to_clean = export_pdf_from_json(mapped, BLANK_PDF_PATH, image_paths_map=img_path_manager) 
            log(f"✅ 빈칸 PDF 저장(정답 숨김 + 마지막 장 정답 모음): {BLANK_PDF_PATH}")
        finally:
            for f in temp_files_to_clean:
                try:
                    os.remove(f)
                    log(f"ℹ 임시 파일 정리: {os.path.basename(f)}")
                except Exception as e:
                    log(f"[WARN] 임시 파일 정리 실패: {os.path.basename(f)}, {e}")
            if temp_files_to_clean:
                log(f"ℹ 총 {len(temp_files_to_clean)}개 임시 파일 정리 완료.")
        
    elif MODE == "quiz":
        log("▶ 예상 문제(JSON) 생성")
        min_clozes = round(total / 3)
        allow_short_answer = QUIZ_ALLOW_SHORT_ANSWER
        data = call_llm_on_text(
            prompt_aggregate_quiz(all_pages_md, min_clozes, allow_short_answer),
            system_prompt=SYSTEM_PROMPT_VISUAL,
        )
        raw_output_path = QUIZ_JSON_PATH.replace(".json", "_raw_llm_output.txt")
        write_text(raw_output_path, json.dumps(data, ensure_ascii=False, indent=2))
        log(f"ℹ LLM 원시 출력 저장: {raw_output_path}")

        quiz_json = {}

        if not isinstance(data, dict):
            quiz_json = {"raw": str(data)}
        elif "multiple_choice" in data or "short_answer" in data:
            quiz_json = data
        elif "clozes" in data:
            quiz_json = {
                "multiple_choice": [],
                "short_answer": [
                    {"q": c.get("text", ""), "a": c.get("answer", "")}
                    for c in data.get("clozes", [])
                ]
            }
        else:
            quiz_json = {"raw": data}
            
        with open(QUIZ_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(quiz_json, f, ensure_ascii=False, indent=2)
        log(f"✅ 예상 문제 JSON 저장: {QUIZ_JSON_PATH}")

    else:
        raise ValueError("MODE must be one of: summary | blank | quiz")

if __name__ == "__main__":
    main()