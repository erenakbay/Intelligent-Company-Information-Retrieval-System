.PHONY: build run stop clean logs shell

build:
	docker-compose build

run:
	docker-compose up

stop:
	docker-compose down

clean:
	docker-compose down --volumes --remove-orphans

logs:
	docker-compose logs -f

shell:
	docker-compose exec fastapi /bin/bash
