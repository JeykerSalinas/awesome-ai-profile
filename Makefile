SHELL := /bin/bash

-include .env.make

IMAGE_NAME ?= app-backend
IMAGE_TAG ?= latest
ACR_LOGIN_SERVER ?= $(if $(ACR_NAME),$(ACR_NAME).azurecr.io)

.PHONY: help install back-install front back dev generate-types type-check build clean docker-back-build docker-back-run docker-back-health azure-login acr-login deploy-back guard-%

help:
	@echo "Available commands:"
	@echo "  make install      Install frontend and backend dependencies"
	@echo "  make back-install Install backend requirements into backend/.venv"
	@echo "  make front        Start the Vite frontend dev server"
	@echo "  make back         Start the FastAPI backend dev server"
	@echo "  make dev          Start frontend and backend together"
	@echo "  make generate-types  Generate frontend event types from backend schemas"
	@echo "  make type-check   Run frontend type checks"
	@echo "  make build        Build the frontend"
	@echo "  make clean        Remove common local cache directories"
	@echo "  make docker-back-build   Build the FastAPI backend Docker image"
	@echo "  make docker-back-run     Run the FastAPI backend container with backend/.env"
	@echo "  make docker-back-health  Check the backend /health endpoint"
	@echo "  make azure-login        Login to Azure manually"
	@echo "  make acr-login          Login to Azure Container Registry"
	@echo "  make deploy-back        Build, push, and deploy the backend container"
	@echo ""
	@echo "Optional local config:"
	@echo "  .env.make              Local Make variables for Azure/deploy settings"

install:
	cd app && npm install
	backend/.venv/bin/pip install -r backend/requirements.txt

back-install:
	cd backend && .venv/bin/pip install -r requirements.txt

front:
	cd app && npm run dev

back:
	cd backend && .venv/bin/python main.py

dev:
	@trap 'kill 0' INT TERM EXIT; \
	$(MAKE) back & \
	$(MAKE) front & \
	wait

generate-types:
	cd backend && .venv/bin/python scripts/generate_event_types.py

type-check:
	cd app && npm run type-check

build:
	cd app && npm run build

docker-back-build:
	docker build -t $(IMAGE_NAME) ./backend

docker-back-run:
	docker run --rm --env-file backend/.env -p 8000:8000 $(IMAGE_NAME)

docker-back-health:
	curl http://localhost:8000/health

clean:
	find backend -type d -name "__pycache__" -prune -exec rm -rf {} +
	find backend -type f -name "*.py[cod]" -delete

azure-login:
	az login

guard-%:
	@test -n "$($*)" || (echo "Missing required variable '$*'. Set it in .env.make or pass it to make." && exit 1)

acr-login: guard-ACR_NAME
	az acr login --name $(ACR_NAME)

deploy-back: guard-ACR_NAME guard-RESOURCE_GROUP guard-CONTAINER_APP_NAME acr-login

deploy-back:
	docker build -t $(IMAGE_NAME) ./backend
	docker tag $(IMAGE_NAME) $(ACR_LOGIN_SERVER)/$(IMAGE_NAME):$(IMAGE_TAG)
	docker push $(ACR_LOGIN_SERVER)/$(IMAGE_NAME):$(IMAGE_TAG)
	az containerapp update \
		--name $(CONTAINER_APP_NAME) \
		--resource-group $(RESOURCE_GROUP) \
		--image $(ACR_LOGIN_SERVER)/$(IMAGE_NAME):$(IMAGE_TAG)
