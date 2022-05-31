#!/bin/bash

# Roman Reggiardo <rreggiar@ucsc.edu>
# 2022_01_12
# see https://github.com/rreggiar/bioconductor_docker
# ssh: git@github.com:rreggiar/bioconductor_docker.git

echo "${USER}"
USER_ID=$(id -u)
echo "UID: "${USER_ID}" "
PORT=$1
echo "mapped port: "${PORT}" "
PROJ=$2
echo "for project: "${PROJ}" "

# user & project specific mounts
DIR="/public/home/"${USER}"/"${PROJ}"/:/home/"${USER}"/"
# rreggiar config file for RSTUDIO looks and behavior
CONFIG="/public/home/"${USER}"/.rstudio_docker_config:/home/"${USER}"/.config/rstudio"
	-v "${CONFIG}" \

echo "making rstudio session hosted at 127.0.0.1:"${PORT}":8787 for "${USER}":"${USER_ID}""
docker run --rm -p 127.0.0.1:"${PORT}":8787 -e DISABLE_AUTH=true \
	-e USER="${USER}" \
	-e USERID="${USER_ID}" \
	-e ROOT=TRUE \
	--name "${PROJ}" \
	--detach \
	-v "${DIR}" \
	kimlab_rstudio:latest
