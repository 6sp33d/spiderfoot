#
# Spiderfoot Dockerfile
#
# http://www.spiderfoot.net
#
# Written by: Michael Pellon <m@pellon.io>
# Updated by: Chandrapal <bnchandrapal@protonmail.com>
# Updated by: Steve Micallef <steve@binarypool.com>
# Updated by: Steve Bate <svc-spiderfoot@stevebate.net>
#    -> Inspired by https://github.com/combro2k/dockerfiles/tree/master/alpine-spiderfoot
#
# Usage:
#
#   sudo docker build -t spiderfoot .
#   sudo docker run -p 5001:5001 --security-opt no-new-privileges spiderfoot
#
# Using Docker volume for spiderfoot data
#
#   sudo docker run -p 5001:5001 -v /mydir/spiderfoot:/var/lib/spiderfoot spiderfoot
#
# Using SpiderFoot remote command line with web server
#
#   docker run --rm -it spiderfoot sfcli.py -s http://my.spiderfoot.host:5001/
#
# Running spiderfoot commands without web server (can optionally specify volume)
#
#   sudo docker run --rm spiderfoot sf.py -h
#
# Running a shell in the container for maintenance
#   sudo docker run -it --entrypoint /bin/sh spiderfoot
#
# Running spiderfoot unit tests in container
#
#   sudo docker build -t spiderfoot-test --build-arg REQUIREMENTS=test/requirements.txt .
#   sudo docker run --rm spiderfoot-test -m pytest test/unit

FROM python:3.12-slim-bookworm AS build
ARG REQUIREMENTS=requirements.txt

# Compilers and headers, only used if a dependency has no binary wheel
# for the target platform. This stage is not part of the final image.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       gcc libc6-dev libffi-dev libssl-dev libxml2-dev libxslt1-dev \
       zlib1g-dev libjpeg62-turbo-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /build
COPY requirements.txt ./requirements.txt
COPY ${REQUIREMENTS} ./${REQUIREMENTS}
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r "$REQUIREMENTS"



FROM python:3.12-slim-bookworm

# Place database and logs outside installation directory
ENV SPIDERFOOT_DATA=/var/lib/spiderfoot
ENV SPIDERFOOT_LOGS=/var/lib/spiderfoot/log
ENV SPIDERFOOT_CACHE=/var/lib/spiderfoot/cache

# Same UID/GID (1000) as the previous Alpine-based image, so existing
# data volumes stay writable after upgrading.
RUN groupadd --gid 1000 spiderfoot \
    && useradd --uid 1000 --gid spiderfoot --home-dir /home/spiderfoot \
       --create-home --shell /usr/sbin/nologin --comment "SpiderFoot User" spiderfoot \
    && mkdir -p "$SPIDERFOOT_DATA" "$SPIDERFOOT_LOGS" "$SPIDERFOOT_CACHE" \
    && chown spiderfoot:spiderfoot "$SPIDERFOOT_DATA" "$SPIDERFOOT_LOGS" "$SPIDERFOOT_CACHE"

WORKDIR /home/spiderfoot
COPY . .
COPY --from=build /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

USER spiderfoot

EXPOSE 5001

# Run the application.
ENTRYPOINT ["/opt/venv/bin/python"]
CMD ["sf.py", "-l", "0.0.0.0:5001"]
