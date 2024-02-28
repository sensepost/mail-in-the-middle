FROM alpine:3.16
LABEL name="Maitm"
COPY *.py /Maitm/
COPY Pipfile* /Maitm/
COPY Maitm /Maitm/Maitm
COPY config /Maitm/config
RUN apk update && \
    apk add python3 && \
    apk add py3-pip && \
    pip install pipenv && \
    cd /Maitm && \ 
    pipenv install --python=3.10
# If flags $FORWARD and $NEWONLY are provided, add the flags
WORKDIR /Maitm
# The user has to provide the parameters in Docker invocation, such as:
# docker run --rm -ti maitm -h
# docker run --rm -ti maitm -c config/config.yml -f -n
ENTRYPOINT [ "pipenv", "run", "python", "./mail-in-the-middle.py" ]

