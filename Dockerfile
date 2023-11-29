# Use a base image with Python installed
# FROM python:3.9-slim-buster
FROM python:3.9

# Set the working directory in the container
WORKDIR /app

# # Ensure package list is up to date, then install and upgrade vulnerable packages
# RUN apt-get update && \
#     apt-get install -y build-essential

RUN apt-get update && apt-get install -y \
    build-essential \
    libffi-dev \
    libssl-dev \
    python3-dev


# Copy the Flask application files to the container
COPY . /app

# upgrade pip
RUN pip install --upgrade pip
RUN pip install --upgrade setuptools

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port 8080
EXPOSE 8080

# Run the Flask application
CMD ["python3", "main.py"]
