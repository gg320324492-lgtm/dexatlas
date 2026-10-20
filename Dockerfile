# syntax=docker/dockerfile:1

FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    DEXATLAS_WORKSPACE=/workspace

# Java is required by the JADX and Apktool backends. Both are invoked as subprocesses
# and are never vendored into the image.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        unzip \
        openjdk-21-jre-headless \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Dependency layer first so source edits do not invalidate the dependency cache.
# uv.lock is committed, so --frozen installs exactly the reviewed set.
#
# The version file is copied in as well, and only it: the build backend reads the
# version from there, so the install cannot work without it. One file does not
# invalidate the layer when the rest of the source changes.
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src/dexatlas/__init__.py ./src/dexatlas/
RUN uv sync --no-dev --extra analysis --frozen

COPY src/ ./src/
RUN uv sync --no-dev --extra analysis --frozen

ENV PATH="/app/.venv/bin:${PATH}" \
    DEXATLAS_JADX_PATH=/opt/jadx/bin/jadx \
    DEXATLAS_APKTOOL_JAR=/opt/apktool/apktool.jar

RUN mkdir -p /opt/jadx /opt/apktool "${DEXATLAS_WORKSPACE}"

# Pinned backend versions, recorded in the image for provenance.
ARG JADX_VERSION=1.5.2
ARG APKTOOL_VERSION=2.11.1

# The jadx archive unpacks directly into bin/ and lib/ — there is no version-named
# top-level directory to move.
RUN curl -fsSL --retry 3 -o /tmp/jadx.zip \
        "https://github.com/skylot/jadx/releases/download/v${JADX_VERSION}/jadx-${JADX_VERSION}.zip" \
    && unzip -q /tmp/jadx.zip -d /opt/jadx \
    && chmod +x /opt/jadx/bin/* \
    && rm /tmp/jadx.zip \
    && test -x /opt/jadx/bin/jadx \
    || { echo "jadx launcher missing after extraction" >&2; ls -R /opt/jadx | head -40 >&2; exit 1; }

RUN curl -fsSL --retry 3 -o /opt/apktool/apktool.jar \
        "https://github.com/iBotPeaches/Apktool/releases/download/v${APKTOOL_VERSION}/apktool_${APKTOOL_VERSION}.jar" \
    && java -jar /opt/apktool/apktool.jar --version

VOLUME ["${DEXATLAS_WORKSPACE}"]

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "dexatlas.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
