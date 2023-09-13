FROM rust:slim

# Install Python
RUN apt-get update && apt-get install -y python3 python3-pip

WORKDIR /app

COPY requirements.txt ./
COPY discord-bot.py ./

RUN pip install -r requirements.txt

CMD ["python3", "discord-bot.py"]