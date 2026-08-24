SHELL := /bin/bash

.PHONY: help install front back dev generate-types type-check build clean docker-back-build docker-back-run docker-back-health

help:
	@echo "Available commands:"
	@echo "  make install      Install frontend and backend dependencies"
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

install:
	cd app && npm install
	backend/.venv/bin/pip install -r backend/requirements.txt

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
	docker build -t awesome-ai-profile-api ./backend

docker-back-run:
	docker run --rm --env-file backend/.env -p 8000:8000 awesome-ai-profile-api

docker-back-health:
	curl http://localhost:8000/health

clean:
	find backend -type d -name "__pycache__" -prune -exec rm -rf {} +
	find backend -type f -name "*.py[cod]" -delete

deploy-back:
	docker build -t awesome-ai-profile-api ./backend
	docker tag awesome-ai-profile-api jeykeraiprofileacr.azurecr.io/awesome-ai-profile-api:latest
	docker push jeykeraiprofileacr.azurecr.io/awesome-ai-profile-api:latest
	az containerapp update \
		--name awesome-ai-profile-api \
		--resource-group awesome-ai-profile \
		--image jeykeraiprofileacr.azurecr.io/awesome-ai-profile-api:latest