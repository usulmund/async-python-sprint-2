ARG arg

FROM ubuntu:latest as app
WORKDIR /media
COPY *.py .
RUN apt update && apt install -y python3

FROM app AS mode_manual
ENV cmd="/bin/bash"

FROM app as mode_test
ENV cmd="python3 tests.py"

FROM app as mode_example
ENV cmd="python3 using_example.py"

FROM mode_$arg as start
CMD $cmd
