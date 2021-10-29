FROM ubuntu:20.04
#RUN python --version
RUN apt-get update -y
RUN apt install -y ffmpeg
RUN apt install -y git
RUN apt-get -y install python3.8
RUN apt-get -y install python3-pip
COPY / /app
WORKDIR /app
RUN pip3 install --upgrade pip
RUN  pip3 install -r requirements.txt
# RUN pip install denoiser
#EXPOSE 5001
CMD ["python3", "flask_server.py" ]