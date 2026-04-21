up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f

backend-dev:
	cd backend && uvicorn app.main:app --reload

frontend-dev:
	cd frontend && npm run dev

restart-backend:
	bash scripts/restart_backend.sh

restart-frontend:
	bash scripts/restart_frontend.sh
