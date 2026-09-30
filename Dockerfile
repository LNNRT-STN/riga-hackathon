# KBC Autopilot prototype: one container for Cloud Run.
FROM node:22-alpine AS web
WORKDIR /web
COPY src/frontend/package.json src/frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY src/frontend/ ./
RUN npm run build

FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PORT=8080 STATIC_DIR=/app/frontend/dist DB_PATH=/tmp/kbc-autopilot.db
WORKDIR /app/backend
COPY src/backend/ ./
COPY --from=web /web/dist /app/frontend/dist
RUN useradd --create-home app
USER app
EXPOSE 8080
CMD ["python", "server.py"]
