# 1. Start with Python
FROM python:3.12-slim

# 2. Define the "home" folder inside the container
WORKDIR /app

# 3. Copy requirements first (for faster builds)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Create the 'server' directory and copy code into it
# This makes /app/server/ the home for your code
COPY . .
# Expose the port FastAPI usually runs on
EXPOSE 8000

# Run uvicorn pointing to your app object
CMD ["python", "-m", "uvicorn", "api.chat:app", "--host", "0.0.0.0", "--port", "8000"]