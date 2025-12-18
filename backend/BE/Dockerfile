FROM python:3.11.9-slim

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y \
    poppler-utils \
    # FFmpeg (MoviePy 필수!)
    ffmpeg \
    # 빌드 도구
    build-essential \
    gcc \
    # PostgreSQL
    libpq-dev \
    postgresql-client \
    # Git
    git \
    # OpenCV 의존성
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    # Chrome/Selenium 의존성
    wget \
    gnupg \
    unzip \
    curl \
    libnss3 \
    libgconf-2-4 \
    libfontconfig1 \
    libxss1 \
    libappindicator3-1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    xdg-utils \
    fonts-liberation \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*


RUN wget -q -O /tmp/google-chrome-stable_current_amd64.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get update \
    && apt-get install -y /tmp/google-chrome-stable_current_amd64.deb \
    && rm /tmp/google-chrome-stable_current_amd64.deb \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# 출력 디렉토리 생성
RUN mkdir -p /app/outputs

# 스크립트 실행 권한 부여
RUN if [ -f ./scripts/entrypoint.sh ]; then chmod +x ./scripts/entrypoint.sh; fi

EXPOSE 8000

# ✅ entrypoint가 있다면 사용, 없으면 직접 uvicorn 실행
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]