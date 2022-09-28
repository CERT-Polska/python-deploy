FROM docker:stable
RUN apk update \
    && apk add python3 curl openssh-client git openssl bash python3-dev libffi-dev openssl-dev gcc libc-dev make py-pip \
    && curl -L https://storage.googleapis.com/kubernetes-release/release/$(curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt)/bin/linux/amd64/kubectl -o /usr/local/bin/kubectl \
    && curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 -o /usr/local/bin/docker-compose \
    && chmod +x /usr/local/bin/kubectl \
    && chmod +x /usr/local/bin/docker-compose

COPY . /app/deploy

RUN cd /app/deploy \
    && pip install . \
