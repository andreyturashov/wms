# WMS Project Makefile

# Colors
GREEN = \033[0;32m
YELLOW = \033[1;33m
NC = \033[0m # No Color

.PHONY: help install install-backend install-frontend run start-backend start-frontend stop clean test

help:
	@echo "$(GREEN)WMS Project Makefile$(NC)"
	@echo ""
	@echo "Available commands:"
	@echo "  make install          - Install all dependencies (backend + frontend)"
	@echo "  make run              - Start both backend and frontend"
	@echo "  make start-backend    - Start only the backend server"
	@echo "  make start-frontend   - Start only the frontend dev server"
	@echo "  make stop             - Stop all running servers"
	@echo "  make clean            - Clean up database and cache files"
	@echo ""

install: install-backend install-frontend
	@echo "$(GREEN)All dependencies installed!$(NC)"

install-backend:
	@echo "$(YELLOW)Installing backend dependencies...$(NC)"
	cd wms-core && uv sync

install-frontend:
	@echo "$(YELLOW)Installing frontend dependencies...$(NC)"
	cd wms-front && yarn install

run: start-backend start-frontend
	@echo "$(GREEN)WMS started!$(NC)"
	@echo "  Backend: http://localhost:8000"
	@echo "  Frontend: http://localhost:5173"
	@echo "  API Docs: http://localhost:8000/docs"

start-backend:
	@echo "$(YELLOW)Starting backend server...$(NC)"
	@pkill -f "uvicorn" 2>/dev/null || true
	@echo "Starting backend on port 8000..."
	@cd wms-core && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 &

start-frontend:
	@echo "$(YELLOW)Starting frontend dev server...$(NC)"
	@pkill -f "vite" 2>/dev/null || true
	@echo "Starting frontend on port 5173..."
	@cd wms-front && /bin/bash -c "source ~/.nvm/nvm.sh && nvm use 20 && npx vite --host 0.0.0.0" &

stop:
	@echo "$(YELLOW)Stopping all servers...$(NC)"
	@pkill -f "uvicorn" 2>/dev/null || true
	@pkill -f "vite" 2>/dev/null || true
	@echo "$(GREEN)Servers stopped!$(NC)"

clean:
	@echo "$(YELLOW)Cleaning up...$(NC)"
	rm -f wms-core/wms.db
	rm -rf wms-core/__pycache__ wms-core/app/__pycache__ wms-core/app/**/__pycache__
	rm -rf wms-core/.pytest_cache
	@echo "$(GREEN)Clean complete!$(NC)"

test:
	@echo "$(YELLOW)Running backend tests...$(NC)"
	cd wms-core && uv run pytest -v
	@echo "$(GREEN)Tests complete!$(NC)"
