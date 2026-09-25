FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/lab
COPY requirements.txt /opt/lab/requirements.txt
RUN pip install --no-cache-dir -r /opt/lab/requirements.txt

COPY . /opt/lab
ENV PYTHONPATH=/opt/lab
ENV LAB_ROOT=/opt/lab
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 18080 18081 18082 18083
CMD ["python", "-m", "uvicorn", "runtime.verify:app", "--host", "0.0.0.0", "--port", "18082"]
