mypy:
	mypy -p rlock

test:
	pytest ./rlock/test/

run:
	uvicorn server:app

queue:
	huey_consumer.py rlock.tasker.huey

build:
	python setup.py sdist

.PHONY: mypy test run queue build
