# syntax=docker/dockerfile:1
FROM node:24-bookworm-slim AS web
WORKDIR /web
COPY frontend/package*.json ./
RUN --mount=type=secret,id=proxy_ca \
    if [ -f /run/secrets/proxy_ca ]; then NODE_EXTRA_CA_CERTS=/run/secrets/proxy_ca npm ci --strict-ssl=true; else npm ci --strict-ssl=true; fi
COPY frontend/ ./
RUN npm run build
FROM python:3.12-slim-bookworm
WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN --mount=type=secret,id=system_ca \
    if [ -f /run/secrets/system_ca ]; then PIP_CERT=/run/secrets/system_ca pip install --no-cache-dir --only-binary=pydantic-core -r backend/requirements.txt; else pip install --no-cache-dir --only-binary=pydantic-core -r backend/requirements.txt; fi
RUN useradd --create-home saly && mkdir /data && chown saly /data
COPY --chown=saly:saly backend/ backend/
COPY --from=web --chown=saly:saly /web/dist frontend/dist
ENV SALY_DATA_DIR=/data SALY_HOST=0.0.0.0
USER saly
EXPOSE 8000
CMD ["python","-m","backend.serve"]
