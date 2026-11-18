# Pandora Coordinator
#
# The coordinator only needs the Python standard library. The Pandora root
# folder (the folder, which is shared with slaves and workstations) has to be
# mounted to /pandora.

FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends gosu tzdata \
    && rm -rf /var/lib/apt/lists/*

COPY Pandora/Scripts/PandoraCoordinator.py \
     Pandora/Scripts/PandoraPaths.py \
     Pandora/Scripts/PandoraPathMap.py \
     Pandora/Scripts/PandoraProtocol.py \
     Pandora/Scripts/PandoraTransport.py \
     /opt/pandora/
COPY docker/entrypoint.sh docker/healthcheck.py /opt/pandora/
RUN chmod 755 /opt/pandora/entrypoint.sh

ENV PANDORA_ROOT=/pandora \
    PANDORA_LOCAL_MODE=true \
    PANDORA_LOG_STDOUT=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PUID=1000 \
    PGID=1000

VOLUME /pandora

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD ["python", "/opt/pandora/healthcheck.py"]

ENTRYPOINT ["/opt/pandora/entrypoint.sh"]
