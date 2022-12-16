.PHONY: venv
	if [ -d .venv ]; then rm -r .venv; fi;
	python3.11 -m venv .venv

.PHONY: reqs
reqs:
	pip3 install --upgrade -r requirements.txt
