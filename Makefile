envs:
	conda info --envs
activate:
	conda activate my_django_env
run:
	DEBUG=1 python manage.py runserver
migrate:
	python manage.py migrate
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