FROM python:3-alpine

WORKDIR /app

RUN pip install --no-cache-dir \
    pytz \
    requests \
    bs4
