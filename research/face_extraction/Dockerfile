# Use an official Python runtime as a parent image
FROM python:3.8-slim

# Set the working directory in the container
WORKDIR /usr/src/app

# Copy the requirements file into the container
COPY requirements.txt ./

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the current directory content into the container
COPY ./ ./

# Command to run the application
CMD ["uvicorn", "extract_face:app", "--host", "0.0.0.0", "--port", "8000"]
