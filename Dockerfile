# QuantLab — reproducible run of the multi-agent intelligence pipeline (offline by default).
# Build:  docker build -t quantlab .
# Run:    docker run --rm quantlab quantlab intel --watchlist NVDA AAPL XOM
# Live:   docker run --rm -e GOOGLE_API_KEY=... quantlab quantlab intel --watchlist NVDA AAPL XOM --live
FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
COPY configs ./configs

# install the package (dev extras include mcp; live extras are optional for Gemini/sources)
RUN pip install --no-cache-dir -e ".[dev]"

# non-root user
RUN useradd -m quant && chown -R quant /app
USER quant

ENTRYPOINT []
CMD ["quantlab", "intel", "--watchlist", "NVDA", "AAPL", "XOM"]
