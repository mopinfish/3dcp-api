envs:
	conda info --envs
activate:
	conda activate my_django_env
run:
	python manage.py runserver
migrate:
	python manage.py migrate
