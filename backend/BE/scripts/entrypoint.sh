#!/bin/bash
cd /app  

# DB가 준비될 때까지 잠시 대기
echo "Waiting for database..."
while ! pg_isready -h db -p 5432 -U ecampus; do
  sleep 1
done

echo "Running Alembic migrations..."
alembic upgrade head

echo "Starting FastAPI server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
