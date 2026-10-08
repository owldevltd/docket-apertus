# Two stages. The first builds the browser app with Node, which is needed for that build only; the second
# runs the Python server with numpy for the pixel fields and psycopg for the store, poppler renders the
# pages. The model is reached over the network (BASE_URL). Nothing of Node is in the image that runs.
FROM node:24-alpine AS app
WORKDIR /build
COPY app/package.json app/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY app ./
RUN npx ng build --output-path /build/out

FROM python:3.11-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends poppler-utils tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir "numpy>=1.26" "psycopg[binary]>=3.1"
COPY src ./src
COPY data ./data
COPY tests ./tests
COPY tools ./tools
COPY Makefile ./
COPY --from=app /build/out ./src/docket/app

ENV PYTHONPATH=/app/src
ENV PORT=8080
ENV TZ=Europe/Zurich
EXPOSE 8080
VOLUME [ "/app/storage" ]

CMD [ "python3", "-m", "docket", "serve" ]
