FROM node:22-alpine AS frontend-build

WORKDIR /frontend

COPY src/react/package.json src/react/package-lock.json ./
RUN npm ci

COPY src/react ./
RUN npm run build

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY --from=frontend-build /frontend/dist ./src/react/dist

EXPOSE 10000

CMD ["sh", "-c", "uvicorn src.server.api:app --host 0.0.0.0 --port ${PORT:-10000}"]
