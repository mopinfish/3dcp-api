envs:
	conda info --envs
activate:
	conda activate my_django_env
run:
	DEBUG=1 python manage.py runserver
migrate:
	python manage.py migrate
migrate-zero:
	python manage.py migrate app_geodjango zero
makemigrations:
	python manage.py makemigrations

# temporary commands

## connect database
pg:
	docker compose exec postgis psql -U geobase

## list databases
pg-ls-db:
	docker compose exec postgis psql -U geobase -c "\l"

## freeze to requirements.txt
freeze:
	pip list --format=freeze > requirements.txt

## create superuser
create_superuser:
	python manage.py custom_createsuperuser

## verceldb
vercel-pg:
	psql -h ep-dark-dew-a1t73g9u-pooler.ap-southeast-1.aws.neon.tech -U geobase -d verceldb
