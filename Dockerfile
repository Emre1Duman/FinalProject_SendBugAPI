FROM python:3.9-buster
RUN apt-get update
COPY ./requirements.txt /app/requirements.txt

RUN pip3 install --upgrade setuptools pip
 
WORKDIR  /app 

RUN apt-get -y install cmake

RUN pip install -r requirements.txt


COPY . /app

ENTRYPOINT [ "python" ]


CMD ["SendBugToSlackV2.py"]


