# Python 기반 이미지
FROM python:3.12-slim

# 환경 변수 설정
# .pyc 파일 생성 방지
ENV PYTHONDONTWRITEBYTECODE=1
# Python 출력 버퍼링 방지
ENV PYTHONUNBUFFERED=1

# 작업 디렉토리 설정
WORKDIR /app

# 4. 시스템 패키지 목록 업데이트 및 필수 개발 도구 설치 (pkg-config 추가!)
RUN apt-get update && apt-get install -y \
    pkg-config \
    default-libmysqlclient-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*


# 종속성 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 프로젝트 복사
COPY . .

# collectstatic 실행 & Gunicorn 실행
CMD ["sh", "-c", "python manage.py collectstatic --noinput && gunicorn -c gunicorn.conf.py skn4th.asgi:application"]

EXPOSE 8000
