# K1: Linux test runner for the parent's suites (Plan v0.4 §6/§7, decisions D24/D26).
# Mirrors frame/Dockerfile.install-security (same pinned base) and the parent CI's
# frame-capture job (pytest + Pillow + Playwright Chromium). Lives in .pi/ only (D20).
FROM debian:bookworm-slim@sha256:abd67ffcfa541b485a3dff59865ab629aa048a6c613e639d36e7456b0b229241

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        ca-certificates \
        php-cli \
        php-sqlite3 \
        python3 \
        python3-venv \
        sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Keep the Playwright pin in step with frame/requirements-shoot.txt (run.sh checks it).
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH=/venv/bin:$PATH
RUN python3 -m venv /venv \
    && pip install --no-cache-dir pytest flake8 Pillow playwright==1.62.0 \
    && playwright install --with-deps chromium \
    && rm -rf /var/lib/apt/lists/*

COPY suite.sh /usr/local/bin/suite.sh
# The checkout may carry CRLF (core.autocrlf=true on the host): normalise.
RUN sed -i 's/\r$//' /usr/local/bin/suite.sh && chmod 0755 /usr/local/bin/suite.sh \
    && useradd -m -u 1000 tester && mkdir /src && chown tester:tester /src

USER tester
WORKDIR /src
