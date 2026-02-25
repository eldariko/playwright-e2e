# Use an official lightweight Python image
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the RCA script into the container
COPY scripts/ai_rca.py /app/scripts/ai_rca.py

# Set the default command to run the script
# We use ENTRYPOINT so arguments can be appended when running the container
ENTRYPOINT ["python", "scripts/ai_rca.py"]