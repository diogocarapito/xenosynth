install:
	pip install --upgrade pip &&\
		pip install -r requirements.txt

test:
	pytest -vv --cov=main --cov=utils --cov=controls --cov=synth tests/test_*.py

format:
	black . *.py

lint:
	pylint --disable=R,C *.py utils/*.py tests/*.py controls/*.py synth/*.py

#container-lint:
#	docker run -rm -i hadolint/hadolint < Dockerfile

refactor:
	format lint

deploy:
	echo "deploy not implemented"

build:
	pyinstaller --name App --onefile --windowed --icon=assets/logo.ico main.py

all: install lint test format