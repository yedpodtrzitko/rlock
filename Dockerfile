FROM python:3.8-alpine

WORKDIR /app
COPY requirements.txt ./

RUN apk add --no-cache --virtual=.build build-base && \
    pip install -r requirements.txt && \
    apk del .build

COPY rlock ./rlock

CMD ["uvicorn", "--host", "0.0.0.0", "rlock.webserver:app"]
