FROM ubuntu:focal as app

RUN apt update && \
  apt-get install -y software-properties-common && \
  apt-add-repository -y ppa:deadsnakes/ppa && apt-get update && \
  apt install -y git-core language-pack-en python3.8-dev python3.8-venv libmysqlclient-dev libffi-dev libssl-dev build-essential gettext openjdk-8-jdk && \
  rm -rf /var/lib/apt/lists/*

ENV VIRTUAL_ENV=/venv
RUN python3.8 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN pip install pip==20.2.3 setuptools==50.3.0

RUN locale-gen en_US.UTF-8
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US:en
ENV LC_ALL en_US.UTF-8
ENV ANALYTICS_API_CFG /edx/etc/analytics_api.yml

WORKDIR /edx/app/analytics_api
COPY requirements /edx/app/analytics_api/requirements
RUN pip install -r requirements/production.txt

EXPOSE 8100
CMD gunicorn --bind=0.0.0.0:8100 --workers 2 --max-requests=1000 -c /edx/app/analytics_api/analytics_data_api/docker_gunicorn_configuration.py analyticsdataserver.wsgi:application

RUN useradd -m --shell /bin/false app
USER app
COPY . /edx/app/analytics_api

FROM app as newrelic
RUN pip install newrelic
CMD newrelic-admin run-program gunicorn --bind=0.0.0.0:8100 --workers 2 --max-requests=1000 -c /edx/app/analytics_api/analytics_data_api/docker_gunicorn_configuration.py analyticsdataserver.wsgi:application
