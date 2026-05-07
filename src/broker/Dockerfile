FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/broker
RUN touch /app/broker/__init__.py

EXPOSE 6000/tcp

ENV PYTHONPATH=/APP
CMD ["python", "-m", "broker.app"]