.PHONY: up down build rebuild logs ps migrate

up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build

rebuild:
	docker compose up -d --build

logs:
	docker compose logs -f

ps:
	docker compose ps

migrate:
	docker compose run --rm migrate
