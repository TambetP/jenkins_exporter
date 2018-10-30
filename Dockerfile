FROM python:2-slim

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

COPY requirements.txt /usr/src/app
RUN pip install --no-cache-dir -r requirements.txt

COPY jenkins_exporter.py /usr/src/app

ENV VIRTUAL_PORT=9118 \
    DEBUG=0

EXPOSE $VIRTUAL_PORT

ENTRYPOINT [ "python", "-u", "./jenkins_exporter.py" ]
