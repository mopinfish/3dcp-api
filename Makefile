up:
	docker compose up -d
shell:
	docker compose exec api python manage.py shell
dbshell:
	docker compose exec api python manage.py dbshell
migrate:
	docker compose exec api python manage.py migrate
migrate-zero:
	docker compose exec api python manage.py migrate app_geodjango zero
makemigrations:
	docker compose exec api python manage.py makemigrations

# temporary commands

## connect database
pg:
	docker compose exec postgis psql -U 3dcp

## list databases
pg-ls-db:
	docker compose exec postgis psql -U 3dcp -c "\l"

## freeze to requirements.txt
freeze:
	docker compose exec api pip list --format=freeze > requirements.txt

## create superuser
exec_create_superuser:
	docker compose exec api python manage.py custom_createsuperuser
exec_create_sample_data:
	docker compose exec api python manage.py create_sample_data

## Fly.io
fly-ssh:
	fly ssh console -C /bin/bash
fly-shell:
	fly ssh console -C "python manage.py shell"
fly-logs:
	fly logs -a 3dcp-api
fly-access-logs:
	fly ssh console -C "tail -f /var/log/nginx/media_access.log"
fly-proxy:
	fly proxy 15432:5432 -a 3dcp-api-db
fly-pg:
	psql -h localhost -U three_cp -d three_cp -p 15432
fly-deploy:
	fly deploy
fly-migrate:
	fly ssh console -C "python manage.py migrate"
