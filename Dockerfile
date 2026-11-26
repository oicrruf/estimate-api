FROM python:3.12.16-alpine3.24@sha256:c5ba3deef00c7758561a0f03c26f44f10589263d40e732b8748e0d1f38f6dd89 AS build
RUN apk upgrade --no-cache
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY src ./src
RUN pip install --no-cache-dir uv==0.7.6 && uv sync --frozen --no-dev

FROM python:3.12.16-alpine3.24@sha256:c5ba3deef00c7758561a0f03c26f44f10589263d40e732b8748e0d1f38f6dd89
RUN apk upgrade --no-cache && addgroup -S estimate && adduser -S -G estimate estimate
WORKDIR /app
COPY --from=build /app/.venv ./.venv
COPY --from=build /app/src ./src
ENV PATH="/app/.venv/bin:$PATH"
USER estimate
EXPOSE 8000
CMD ["uvicorn", "estimate_api.app:app", "--host", "0.0.0.0", "--port", "8000"]
