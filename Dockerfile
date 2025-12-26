ARG PYTHON_VERSION=3.12-bookworm
FROM python:${PYTHON_VERSION}

ENV TZ="Asia/Tokyo"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# aptの設定をシンプルかつ堅牢にする
RUN rm -f /etc/apt/apt.conf.d/99custom && \
    echo 'Acquire::Retries "3";' > /etc/apt/apt.conf.d/80-retries && \
    echo 'Acquire::http::Pipeline-Depth "0";' >> /etc/apt/apt.conf.d/80-retries

# 既存の不安定なソースリストを一旦リセットし、日本のミラーに固定
RUN echo "deb http://ftp.jp.debian.org/debian bookworm main" > /etc/apt/sources.list && \
    echo "deb http://ftp.jp.debian.org/debian bookworm-updates main" >> /etc/apt/sources.list && \
    echo "deb http://security.debian.org/debian-security bookworm-security main" >> /etc/apt/sources.list

# インストールを一気に行う（キャッシュ汚染を防ぐため）
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    libpq-dev \
    build-essential \
    gdal-bin \
    libgdal-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 以降の GDAL 設定などは変更なし
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

RUN mkdir -p /code
WORKDIR /code

COPY ./nginx/nginx.conf /etc/nginx/nginx.conf
COPY requirements.txt /tmp/requirements.txt

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /tmp/requirements.txt

COPY . /code
RUN python manage.py collectstatic --noinput

EXPOSE 8080 8000
CMD service nginx start && gunicorn core.wsgi:application --bind 0.0.0.0:8000