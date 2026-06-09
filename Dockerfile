FROM python:3.14
WORKDIR /app

RUN pip install --upgrade pip

COPY requirements.txt /app/

RUN pip install --no-cache-dir -r requirements.txt

RUN apt update -y
RUN apt install -y firefox-esr

COPY mensa.py /app/mensa.py
COPY src /app/src
COPY secret /app/secret

CMD python -u mensa.py -lg bi -su 15tjecufht8s5mxcrt3u967cyy -d 08:00
