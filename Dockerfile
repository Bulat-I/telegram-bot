FROM quay.io/centos/centos:stream9
RUN yum install -y sudo
RUN yum install -y epel-release
RUN yum install -y python
RUN yum clean all
WORKDIR /app
RUN chmod 777 /app
RUN python -m venv /opt/venv
COPY ./common/*.py ./common/
COPY ./filters/*.py ./filters/
COPY ./handlers/*.py ./handlers/
COPY ./keyboards/*.py ./keyboards/
COPY ./locales/en/* ./locales/en/
COPY ./locales/ru/* ./locales/ru/
COPY ./middlewares/*.py ./middlewares/
COPY ./workload_handlers/*.py ./workload_handlers/
COPY .env .
COPY app.py .
COPY requirements.txt .
RUN /opt/venv/bin/pip install --upgrade pip
RUN /opt/venv/bin/pip install --verbose -r requirements.txt && /opt/venv/bin/pip freeze
COPY app.py .
ENTRYPOINT ["/opt/venv/bin/python", "app.py"]
