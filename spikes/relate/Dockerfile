FROM python:3.12.14-slim@sha256:f77ac9e44ae96ef2c90b8053ea08c31f8be030f824196b0ae4db6d462c84e51f

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /probe
COPY requirements-container.txt .
COPY wheelhouse/ ./wheelhouse/
RUN python -m pip install --no-index --find-links=wheelhouse --only-binary=:all: --require-hashes -r requirements-container.txt
COPY catalog.json spike.py container_probe.py ./
RUN addgroup --system probe && adduser --system --ingroup probe probe \
    && mkdir -p /data /backup /restored \
    && chown probe:probe /data /backup /restored \
    && chmod -R a+rX /probe
USER probe
ENTRYPOINT ["python", "/probe/container_probe.py"]
