FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Copy source code
COPY src/ src/

# Create blogs directory
RUN mkdir -p /app/blogs

ENTRYPOINT ["python", "-m", "blog_generator.cli"]
