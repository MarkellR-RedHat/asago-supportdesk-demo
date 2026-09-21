# One image, many entrypoints: each Deployment/Job overrides the command.
#   podman build -t quay.io/<you>/asago-supportdesk-demo:latest -f Containerfile .
FROM registry.access.redhat.com/ubi9/python-312

USER 0
RUN dnf install -y git && dnf clean all
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir . \
    # OpenShift's restricted SCC runs the container as a random UID with GID 0.
    && chgrp -R 0 /app && chmod -R g=u /app
USER 1001
EXPOSE 8000 8080 8081 8082
