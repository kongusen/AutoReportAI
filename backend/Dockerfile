# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set environment variables for better container operation
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Create a non-root user and group
RUN addgroup --system app && adduser --system --group app

# Set the working directory in the container
WORKDIR /app

# Copy and install dependencies first to leverage Docker layer caching
COPY ./requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

# Copy the rest of the application code
COPY . /app

# Grant ownership of the app directory to the non-root user
RUN chown -R app:app /app

# Switch to the non-root user
USER app

# Expose port 8000 for the API
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
