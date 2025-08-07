import multiprocessing

# CPU 코어 수 가져오기
cpu_count = multiprocessing.cpu_count()

# 워커 프로세스 개수 계산 공식
workers = (cpu_count * 2) + 1
print(workers)  # 25 (물리코어 6, 논리코어 12인 경우)

bind = "0.0.0.0:8000"  # 바인드할 주소와 포트
worker_class = "uvicorn.workers.UvicornWorker"
timeout = 30  # 요청 타임아웃 (초 단위)
