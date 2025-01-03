#ARG PYTHON_VERSION=3.12-slim
#FROM python:${PYTHON_VERSION}
FROM continuumio/miniconda3

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN echo "Acquire::http::Pipeline-Depth 0;" > /etc/apt/apt.conf.d/99custom && \
    echo "Acquire::http::No-Cache true;" >> /etc/apt/apt.conf.d/99custom && \
    echo "Acquire::BrokenProxy    true;" >> /etc/apt/apt.conf.d/99custom && \
    echo 'Acquire::http::Timeout "300";' > /etc/apt/apt.conf.d/99timeout
RUN apt-get clean && rm -rf /var/lib/apt/lists/*
# install psycopg2 dependencies.
RUN apt-get update && apt-get install -y  --fix-missing \
    libpq-dev \
    build-essential \
    && apt-get install -y --no-install-recommends gdal-bin libgdal-dev

# Set environment variables for GDAL
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

RUN mkdir -p /code
WORKDIR /code

COPY requirements.txt /tmp/requirements.txt
RUN set -ex && \
    pip install --upgrade pip && \
    pip install -r /tmp/requirements.txt && \
    rm -rf /root/.cache/

# Install GDAL python bindings
ENV GDAL_VERSION=3.7.3
ENV GDAL_CONFIG=/usr/local/bin/gdal-config
RUN conda install -c conda-forge gdal

COPY . /code

ENV SECRET_KEY="MzfLZo4vgzkGfOu0yWXiayO0PXFBv9ntdZCNCpDbe3HTXcFu1x"
RUN python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["gunicorn","--bind",":8000","--workers","2","my_django.wsgi"]
