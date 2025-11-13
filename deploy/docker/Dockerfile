FROM docker:dind
RUN apk update \
    && apk add python3 curl openssh-client git openssl bash py-pip \
    && curl -L https://storage.googleapis.com/kubernetes-release/release/$(curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt)/bin/linux/amd64/kubectl -o /usr/local/bin/kubectl \
    && chmod +x /usr/local/bin/kubectl

COPY . /app/deploy

RUN cd /app/deploy \
    && pip install . --break-system-packages