FROM python:3.13-bookworm

RUN mkdir -p /usr/src/app
RUN useradd -m dsuploader

WORKDIR /usr/src/app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

USER dsuploader
CMD ["python", "main.py"]
