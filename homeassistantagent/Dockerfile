FROM node:20-alpine AS web-build

WORKDIR /app/web

COPY web/package.json /app/web/package.json
COPY web/package-lock.json /app/web/package-lock.json
RUN npm ci

COPY web /app/web
RUN npm run build

FROM python:3.11-alpine

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY server.py /app/server.py
COPY config_parser.py /app/config_parser.py
COPY run.sh /app/run.sh
COPY --from=web-build /app/web/dist /app/web/dist

RUN chmod +x /app/run.sh

CMD ["/app/run.sh"]
