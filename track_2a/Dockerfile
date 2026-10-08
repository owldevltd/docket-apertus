# Docket runs on Python with numpy for the pixel fields and psycopg for the store; poppler renders the pages.
# The model is reached over the network (BASE_URL). No build step.
FROM python:3.11-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir "numpy>=1.26" "psycopg[binary]>=3.1"
COPY src ./src
COPY data ./data
COPY tests ./tests
COPY tools ./tools
COPY Makefile ./

ENV PYTHONPATH=/app/src
ENV PORT=8080
EXPOSE 8080
VOLUME [ "/app/storage" ]

CMD [ "python3", "-m", "docket", "serve" ]
