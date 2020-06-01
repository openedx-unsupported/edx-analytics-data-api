FROM ubuntu:xenial as app

RUN apt update && \
  apt install -y git-core language-pack-en python3.5 python3-pip python3-dev libmysqlclient-dev libffi-dev libssl-dev build-essential gettext openjdk-8-jdk && \
  pip3 install --upgrade pip setuptools && \
  rm -rf /var/lib/apt/lists/*


RUN ln -s /usr/bin/pip3 /usr/bin/pip
RUN ln -s /usr/bin/python3 /usr/bin/python


RUN locale-gen en_US.UTF-8
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US:en
ENV LC_ALL en_US.UTF-8
ENV ANALYTICS_API_CFG /edx/etc/analytics_api.yml

WORKDIR /edx/app/analytics_api
COPY requirements /edx/app/analytics_api/requirements
RUN pip3 install -r requirements/production.txt

EXPOSE 8100
CMD gunicorn --bind=0.0.0.0:8100 --workers 2 --max-requests=1000 -c /edx/app/analytics_api/analytics_data_api/docker_gunicorn_configuration.py analyticsdataserver.wsgi:application

RUN useradd -m --shell /bin/false app
USER app
COPY . /edx/app/analytics_api

FROM app as newrelic
RUN pip3 install newrelic
CMD newrelic-admin run-program gunicorn --bind=0.0.0.0:8100 --workers 2 --max-requests=1000 -c /edx/app/analytics_api/analytics_data_api/docker_gunicorn_configuration.py analyticsdataserver.wsgi:application
