# Use an official lightweight Python image.
FROM python:3.11-slim

# Set the working directory in the container to /app
WORKDIR /app

# Copy the dependencies file to the working directory
COPY requirements.txt .

# Install any dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the content of the local src directory to the working directory
COPY . .

# Inform Docker that the container listens on the specified network ports at runtime.
# Google Cloud Run does not require the EXPOSE directive, but it's good practice.
EXPOSE 8080

# Command to run on container start
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080"]
