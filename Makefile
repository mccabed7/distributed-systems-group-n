COMPOSE_FILE := infrastructure/docker-compose.yml
COMPOSE := docker compose -f $(COMPOSE_FILE)

.PHONY: up down build logs

up:
	$(COMPOSE) up $(ARGS)

down:
	$(COMPOSE) down

build:
	$(COMPOSE) build

logs:
	$(COMPOSE) logs -f $(ARGS)
