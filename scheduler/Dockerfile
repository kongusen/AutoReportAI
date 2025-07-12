# Use the same official Python runtime as the backend
FROM python:3.9-slim

# Set environment variables for better container operation
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Create a non-root user and group
RUN addgroup --system app && adduser --system --group app

# Set the working directory in the container
WORKDIR /app

# The scheduler shares dependencies with the backend.
# Copy requirements from the backend directory and install them.
COPY ../backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

# Copy the entire application context into the container.
# This is needed because the scheduler imports from the `app` module.
COPY . /app

# Grant ownership of the app directory to the non-root user
RUN chown -R app:app /app

# Switch to the non-root user
USER app

# Command to run the scheduler
CMD ["python", "scheduler/main.py"] 