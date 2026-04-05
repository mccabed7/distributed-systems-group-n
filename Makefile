COMPOSE_FILE := infrastructure/docker-compose.yml
COMPOSE := docker compose -f $(COMPOSE_FILE)
UI_PID_FILE := .ui.pid
UI_LOG_FILE := .ui.log

.PHONY: up down build logs

up:
	@if [ ! -f $(UI_PID_FILE) ]; then \
		echo "Starting ui..."; \
		rm $(UI_LOG_FILE); \
		npm --prefix ui run dev > $(UI_LOG_FILE) 2>&1 & echo $$! > $(UI_PID_FILE); \
	fi
	$(COMPOSE) up $(ARGS)

down:
	@if [ -f $(UI_PID_FILE) ]; then \
		echo "Stopping ui..."; \
		kill $$(cat $(UI_PID_FILE)) && rm $(UI_PID_FILE); \
	fi
	$(COMPOSE) down

build:
	$(COMPOSE) build
	npm --prefix ui install

logs:
	@if [ "$(ARGS)" = "ui" ]; then \
		tail -f $(UI_LOG_FILE); \
	else \
		$(COMPOSE) logs -f $(ARGS); \
	fi
