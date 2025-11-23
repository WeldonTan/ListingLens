APP=listinglens
GIT_SHA=$(shell git rev-parse --short HEAD)

.PHONY: up down build logs

up:
	docker-compose up -d --build

down:
	docker-compose down

logs:
	docker-compose logs -f

build:
	docker build -t $(APP):$(GIT_SHA) .

# For development
dev:
	docker-compose up --build
