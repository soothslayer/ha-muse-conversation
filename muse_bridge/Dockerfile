FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-venv python3-dbus python3-gi python3-cryptography \
    ca-certificates curl git && rm -rf /var/lib/apt/lists/*
COPY musegadget-spoken-replies.patch /tmp/bridge.patch
RUN curl -fsSL https://github.com/facebookincubator/muse-gadget-sdk/archive/3229892e93c18a768ace42cbe1fe7133f91ca203.tar.gz -o /tmp/sdk.tar.gz \
    && echo "38bf8267e9418b61c3e2cbf84fc0eae5c1506464d31e2e11376719d991a83f97  /tmp/sdk.tar.gz" | sha256sum -c - \
    && mkdir /tmp/sdk && tar xzf /tmp/sdk.tar.gz -C /tmp/sdk --strip-components=1 \
    && cd /tmp/sdk && git apply /tmp/bridge.patch \
    && python3 -m venv --system-site-packages /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir ./linux \
    && rm -rf /tmp/sdk /tmp/sdk.tar.gz /tmp/bridge.patch
COPY main.py /app/main.py
ENV PYTHONUNBUFFERED=1
CMD ["/opt/venv/bin/python", "/app/main.py"]

ARG BUILD_VERSION=0.3.11
ARG BUILD_ARCH
LABEL io.hass.version="${BUILD_VERSION}" io.hass.type="app" io.hass.arch="${BUILD_ARCH}"
