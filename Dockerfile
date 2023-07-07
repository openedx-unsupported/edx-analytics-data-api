FROM ubuntu:focal as base

# System requirements.

# pkg-config; mysqlclient>=2.2.0 requires pkg-config (https://github.com/PyMySQL/mysqlclient/issues/620)

RUN apt update && \
  DEBIAN_FRONTEND=noninteractive apt-get install -qy \ 
  curl \
  vim \
  language-pack-en \
  build-essential \
  python3.8-dev \
  python3-virtualenv \
  python3.8-distutils \
  libmysqlclient-dev \
  pkg-config \
  libssl-dev && \
  rm -rf /var/lib/apt/lists/*

# Use UTF-8.
RUN locale-gen en_US.UTF-8
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US:en
ENV LC_ALL en_US.UTF-8

ARG COMMON_APP_DIR="/edx/app"
ARG ANALYTICS_API_SERVICE_NAME="analytics_api"
ENV ANALYTICS_API_HOME "${COMMON_APP_DIR}/${ANALYTICS_API_SERVICE_NAME}"
ARG ANALYTICS_API_APP_DIR="${COMMON_APP_DIR}/${ANALYTICS_API_SERVICE_NAME}"
ARG ANALYTICS_API_VENV_DIR="${COMMON_APP_DIR}/${ANALYTICS_API_SERVICE_NAME}/venvs/${ANALYTICS_API_SERVICE_NAME}"
ARG ANALYTICS_API_CODE_DIR="${ANALYTICS_API_APP_DIR}/${ANALYTICS_API_SERVICE_NAME}"

ENV ANALYTICS_API_CODE_DIR="${ANALYTICS_API_CODE_DIR}"
ENV PATH "${ANALYTICS_API_VENV_DIR}/bin:$PATH"
ENV COMMON_CFG_DIR "/edx/etc"
ENV ANALYTICS_API_CFG "/edx/etc/${ANALYTICS_API_SERVICE_NAME}.yml"

# Working directory will be root of repo.
WORKDIR ${ANALYTICS_API_CODE_DIR}

RUN virtualenv -p python3.8 --always-copy ${ANALYTICS_API_VENV_DIR}

# Expose canonical Analytics port
EXPOSE 19001

FROM base as prod

ENV DJANGO_SETTINGS_MODULE "analyticsdataserver.settings.production"

COPY requirements/production.txt ${ANALYTICS_API_CODE_DIR}/requirements/production.txt

RUN pip install -r ${ANALYTICS_API_CODE_DIR}/requirements/production.txt

# Copy over rest of code.
# We do this AFTER requirements so that the requirements cache isn't busted
# every time any bit of code is changed.

COPY . .

# exec /edx/app/analytics_api/venvs/analytics_api/bin/gunicorn -c /edx/app/analytics_api/analytics_api_gunicorn.py  analyticsdataserver.wsgi:application

CMD ["gunicorn" , "-b", "0.0.0.0:8100", "--pythonpath", "/edx/app/analytics_api/analytics_api","analyticsdataserver.wsgi:application"]

FROM base as dev

ENV DJANGO_SETTINGS_MODULE "analyticsdataserver.settings.devstack"

COPY requirements/dev.txt ${ANALYTICS_API_CODE_DIR}/requirements/dev.txt

RUN pip install -r ${ANALYTICS_API_CODE_DIR}/requirements/dev.txt

# Copy over rest of code.
# We do this AFTER requirements so that the requirements cache isn't busted
# every time any bit of code is changed.
COPY . .

# Devstack related step for backwards compatibility
RUN touch /edx/app/${ANALYTICS_API_SERVICE_NAME}/${ANALYTICS_API_SERVICE_NAME}_env

CMD while true; do python ./manage.py runserver 0.0.0.0:8110; sleep 2; done
