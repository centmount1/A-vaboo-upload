FROM mcr.microsoft.com/devcontainers/python:1-3.11-bullseye
ENV PYTHONUNBUFFERED 1

# Time Zone
ENV TZ Asia/Tokyo

# Language
ENV LANG ja_JP.UTF-8
ENV LANGUAGE ja_JP:ja
ENV LC_ALL ja_JP.UTF-8

# Install ffmpeg
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
   && apt-get -y install --no-install-recommends ffmpeg \
   && rm -rf /var/lib/apt/lists/*

# Install PostgreSQL client
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
   && apt-get -y install --no-install-recommends postgresql-client

COPY requirements.txt /tmp/pip-tmp/
RUN pip3 --disable-pip-version-check --no-cache-dir install -r /tmp/pip-tmp/requirements.txt \
   && rm -rf /tmp/pip-tmp

# Set the working directory
WORKDIR /workspaces/${localWorkspaceFolderBasename}
