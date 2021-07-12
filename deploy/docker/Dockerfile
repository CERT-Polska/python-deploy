FROM docker:stable
RUN apk update \
    && apk add python3 curl openssh-client git openssl bash python-dev libffi-dev openssl-dev gcc libc-dev make py-pip \
    && curl -L https://storage.googleapis.com/kubernetes-release/release/$(curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt)/bin/linux/amd64/kubectl -o /usr/local/bin/kubectl \
    && chmod +x /usr/local/bin/kubectl \
    && pip install docker-compose

COPY . /app/deploy

RUN cd /app/deploy \
    && python3 setup.py install
