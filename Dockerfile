FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY cryptic ./cryptic

RUN pip install --no-cache-dir .

# /vaults: bind-mount the host directory tree containing every vault's
#          input/output/originals subdirectories referenced in config.yaml.
# /config: bind-mount a host directory that contains config.yaml.
VOLUME ["/vaults", "/config"]

ENTRYPOINT ["cryptic", "service", "--config", "/config/config.yaml"]
