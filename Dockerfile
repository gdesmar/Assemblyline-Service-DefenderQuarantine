ARG branch=latest
FROM cccs/assemblyline-v4-service-base:$branch AS base

ENV SERVICE_PATH DefenderQuarantine.DefenderQuarantine.DefenderQuarantine

USER root

FROM base AS build

RUN apt-get update && apt-get install -y build-essential libssl-dev wget && rm -rf /var/lib/apt/lists/*

FROM base

USER assemblyline

WORKDIR /opt/al_service
COPY . .

ARG version=4.0.0.dev1
USER root
RUN sed -i -e "s/\$SERVICE_TAG/$version/g" service_manifest.yml

USER assemblyline