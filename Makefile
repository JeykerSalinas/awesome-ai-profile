SHELL := /bin/bash

.PHONY: help install front back dev type-check build clean

help:
	@echo "Available commands:"
	@echo "  make install      Install frontend and backend dependencies"
	@echo "  make front        Start the Vite frontend dev server"
	@echo "  make back         Start the FastAPI backend dev server"
	@echo "  make dev          Start frontend and backend together"
	@echo "  make type-check   Run frontend type checks"
	@echo "  make build        Build the frontend"
	@echo "  make clean        Remove common local cache directories"

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

type-check:
	cd app && npm run type-check

build:
	cd app && npm run build

clean:
	find backend -type d -name "__pycache__" -prune -exec rm -rf {} +
	find backend -type f -name "*.py[cod]" -delete
