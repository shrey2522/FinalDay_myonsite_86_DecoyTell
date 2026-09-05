FROM python:3.12-slim

WORKDIR /app

COPY . .

CMD ["sh", "/app/verify.sh"]