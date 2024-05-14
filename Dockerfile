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

# Copy start.sh script into the image
COPY start.sh /workspaces/A-vaboo-upload/start.sh

# Give execute permission to the start.sh script
RUN chmod +x /workspaces/A-vaboo-upload/start.sh

# Execute start.sh and then run Python scripts
CMD ["/bin/bash", "-c", "/workspaces/A-vaboo-upload/start.sh"]
