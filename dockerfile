FROM python:3.12.3-bookworm

COPY requirements.txt /requirements.txt

COPY . /app

RUN python -m pip install -r /requirements.txt && mkdir /file && mkdir /logs && mkdir /backup &&\
    apt update && apt install zip

WORKDIR /app

CMD cd /app && gunicorn -w $(nproc) -b 0.0.0.0:443 wsgi:app --timeout 3600 --keyfile /app/cert/key.pem --certfile /app/cert/cert.pem