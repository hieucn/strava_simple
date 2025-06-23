FROM python:3.9-slim

RUN apt-get update && apt-get install -y chromium-driver
# Set the working directory
WORKDIR /app

# Copy the requirements file
COPY requirements.txt .
# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application source code
COPY . .

# Set environment variables
ENV FLASK_APP=running_challenge_app.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=5001

# Expose the port the app runs on
EXPOSE 5001

# Command to run the application
CMD ["flask", "run"]