FROM python:3.10.3-alpine

RUN apk update
RUN apk add nano

RUN mkdir wd
WORKDIR /wd
COPY app/requirements.txt .
RUN pip install -r requirements.txt

COPY app/ ./

CMD ["gunicorn", "--threads=1", "-b 0.0.0.0:80", "app:server"]