mypy:
	mypy -p rlock

test:
	pytest ./rlock/test/

run:
	uvicorn server:app

queue:
	huey_consumer.py rlock.tasker.huey

.PHONY: mypy test run queue
