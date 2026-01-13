FROM python:3.11-alpine

WORKDIR /app

COPY server.py /app/server.py
COPY run.sh /app/run.sh

RUN chmod +x /app/run.sh

CMD ["/app/run.sh"]
