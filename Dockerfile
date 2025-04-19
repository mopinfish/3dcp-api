ARG PYTHON_VERSION=3.12-slim
FROM python:${PYTHON_VERSION}

ENV TZ="Asia/Tokyo"

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN echo "Acquire::http::Pipeline-Depth 0;" > /etc/apt/apt.conf.d/99custom && \
    echo "Acquire::http::No-Cache true;" >> /etc/apt/apt.conf.d/99custom && \
    echo "Acquire::BrokenProxy    true;" >> /etc/apt/apt.conf.d/99custom && \
    echo 'Acquire::http::Timeout "300";' > /etc/apt/apt.conf.d/99timeout
# install psycopg2 dependencies.
RUN apt-get update && apt-get install -y  --fix-missing \
    nginx \
    libpq-dev \
    build-essential \
    && apt-get install -y --no-install-recommends gdal-bin libgdal-dev

# Set environment variables for GDAL
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

RUN mkdir -p /code
WORKDIR /code

# Nginx設定をコピー
COPY ./nginx/nginx.conf /etc/nginx/nginx.conf

COPY requirements.txt /tmp/requirements.txt
RUN set -ex && \
    pip install --upgrade pip && \
    pip install -r /tmp/requirements.txt && \
    rm -rf /root/.cache/

# Install GDAL python bindings
ENV GDAL_VERSION=3.6.2
ENV GDAL_CONFIG=/usr/bin/gdal-config
ENV GDAL_LIBRARY_PATH=/usr/lib/aarch64-linux-gnu/libgdal.so

COPY . /code

RUN python manage.py collectstatic --noinput

EXPOSE 8080
EXPOSE 8000

# NginxとDjangoを起動するスクリプトを用意
CMD service nginx start && gunicorn core.wsgi:application --bind 0.0.0.0:8000
