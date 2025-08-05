# Python 기반 이미지
FROM python:3.12-slim

# 작업 디렉토리 설정
WORKDIR /app

# 종속성 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 프로젝트 복사
COPY . .

# collectstatic 실행 & Gunicorn 실행
CMD ["sh", "-c", "python manage.py collectstatic --noinput && gunicorn skn4th.wsgi:application --bind 0.0.0.0:8000"]

EXPOSE 8000
