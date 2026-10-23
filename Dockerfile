# Node 20 is no longer an approved production-build runtime. Keep this pinned
# to a patched release so certificate and runtime fixes cannot drift backward.
FROM node:22.23.4-bookworm AS frontend-build

WORKDIR /src/frontend
COPY package.json ./
RUN npm install --no-audit --no-fund
COPY public/ ./public/
COPY src/ ./src/
ENV REACT_APP_BACKEND_URL=""
RUN npm run build

FROM python:3.13-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -r /app/requirements.txt
COPY backend/ /app/backend/
COPY server.py /app/backend/server.py
COPY --from=frontend-build /src/frontend/build /app/frontend/build
WORKDIR /app/backend
CMD ["sh", "-c", "exec uvicorn production:app --host 0.0.0.0 --port ${PORT:-8080}"]
