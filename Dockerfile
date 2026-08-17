FROM node:20-bookworm AS frontend-build

WORKDIR /src/frontend
COPY frontend/package.json frontend/yarn.lock ./
RUN corepack enable \
    && corepack prepare yarn@1.22.22 --activate \
    && yarn install --frozen-lockfile
COPY frontend/ ./
ENV REACT_APP_BACKEND_URL=""
RUN yarn build

FROM python:3.11-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt /app/backend/requirements.txt
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -r /app/backend/requirements.txt
COPY . /app/backend/
COPY --from=frontend-build /src/frontend/build /app/frontend/build
WORKDIR /app/backend
CMD ["sh", "-c", "exec uvicorn production:app --host 0.0.0.0 --port ${PORT:-8080}"]