.PHONY: up down logs migrate seed test

up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f

migrate:
	docker compose run --rm django python manage.py migrate

seed:
	docker compose run --rm django python manage.py seed_demo

test:
	docker compose run --rm fastapi pytest
	docker compose run --rm django python manage.py test
	docker compose run --rm frontend npm test -- --run
