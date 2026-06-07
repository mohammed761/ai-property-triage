.PHONY: build up down logs ps seed-rag smoke-test service-io-report assert-service-report test

build:
	docker compose build

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f

ps:
	docker compose ps

seed-rag:
	docker compose run --rm --no-deps rag-service python scripts/populate_chroma.py
	docker compose restart rag-service langgraph-agent

smoke-test:
	./scripts/smoke_test.sh

service-io-report:
	./scripts/write_service_io_report.sh

assert-service-report:
	python3 scripts/assert_service_io_report.py

test: up seed-rag smoke-test service-io-report assert-service-report
