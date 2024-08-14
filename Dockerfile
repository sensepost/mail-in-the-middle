FROM alpine:3.20
LABEL name="Maitm"
LABEL "com.example.vendor"="Orange Cyberdefense Sensepost Team"
LABEL org.opencontainers.image.authors="Felipe Molina de la Torre"

COPY *.py /Maitm/
COPY Pipfile /Maitm/
COPY Maitm /Maitm/Maitm
COPY config /Maitm/config
RUN apk update && \
    apk add python3 && \
    apk add py3-pip && \
    apk add gcc && \
    apk add python3-dev && \
    apk add libc-dev && \
    apk add libffi-dev && \
    apk add pipx && \
    apk add yaml-dev
# Uninstalling setuptools as it produces this error: https://github.com/pypa/setuptools/issues/4483
# It will be installed later during pipenv install command
# Update the path to have pipx tools available in the command line
ENV PATH="$PATH:/root/.local/bin"
RUN pipx install pipenv
WORKDIR /Maitm
# RUN cd /Maitm
RUN pipenv install --python=3.12

# The user has to provide the parameters in Docker invocation, such as:
# docker run --rm -ti maitm -h
# docker run --rm -ti maitm -c config/config.yml -f -n
ENTRYPOINT [ "pipenv", "run", "python", "./mail-in-the-middle.py" ]
