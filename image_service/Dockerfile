FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

RUN pip install --upgrade pip
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu "torch>=2.2,<3" "torchvision>=0.17,<1"
RUN pip install --no-cache-dir \
    "fastapi>=0.111.0,<1" \
    "uvicorn[standard]>=0.30.0,<1" \
    "pydantic>=2.7,<3" \
    "pillow>=10.0.0,<12" \
    "requests>=2.31.0,<3"

COPY app ./app

EXPOSE 8000

CMD ["uvicorn", "app.app:app", "--host", "0.0.0.0", "--port", "8000"]
