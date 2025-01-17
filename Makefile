envs:
	conda info --envs
activate:
	conda activate my_django_env
run:
	DEBUG=1 python manage.py runserver 0.0.0.0:8000
shell:
	docker compose exec web python manage.py shell
dbshell:
	docker compose exec web python manage.py dbshell
migrate:
	docker compose exec web python manage.py migrate
migrate-zero:
	docker compose exec web python manage.py migrate app_geodjango zero
makemigrations:
	docker compose exec web python manage.py makemigrations

# temporary commands

## connect database
pg:
	docker compose exec postgis psql -U geobase

## list databases
pg-ls-db:
	docker compose exec postgis psql -U geobase -c "\l"

## freeze to requirements.txt
freeze:
	docker compose exec web pip list --format=freeze > requirements.txt

## create superuser
exec_create_superuser:
	docker compose exec web python manage.py custom_createsuperuser
exec_create_sample_data:
	docker compose exec web python manage.py create_sample_data

## verceldb
vercel-pg:
	psql -h ep-dark-dew-a1t73g9u-pooler.ap-southeast-1.aws.neon.tech -U geobase -d verceldb

## Fly.io
fly-ssh:
	fly ssh console -C /bin/bash
fly-shell:
	fly ssh console -C "python manage.py shell"
fly-logs:
	fly logs -a my-django
fly-access-logs:
	fly ssh console -C "tail -f /var/log/nginx/media_access.log"
fly-proxy:
	fly proxy 15432:5432 -a my-django-db
fly-pg:
	psql -h localhost -U geobase -d geobase -p 15432
fly-deploy:
	fly deploy
fly-migrate:
	fly ssh console -C "python manage.py migrate"
