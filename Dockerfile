FROM python:3.12-slim
WORKDIR /app

ENV PYTHONPATH=/app/src
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV PATH="/opt/venv/bin:/root/.local/bin/:$PATH"

# The installer requires curl (and certificates) to download the release archive
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates

# Download the latest installer
ADD https://astral.sh/uv/install.sh /uv-installer.sh

# Run the installer then remove it
RUN sh /uv-installer.sh && rm /uv-installer.sh

# Ensure the installed binary is on the `PATH`
ENV PATH="/root/.local/bin/:$PATH"

# Copy uv required files to working dir
COPY pyproject.toml .python-version uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

ARG SOURCE_MODEL=de_core_news_sm
ARG TARGET_MODEL=es_core_news_sm

RUN /opt/venv/bin/python -m spacy download $SOURCE_MODEL
RUN /opt/venv/bin/python -m spacy download $TARGET_MODEL

ENTRYPOINT ["/opt/venv/bin/python", "-m", "lexharvest"]
CMD []
