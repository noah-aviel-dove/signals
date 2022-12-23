.PHONY: venv
venv:
	if [ -d .venv ]; then rm -r .venv; fi;
	python3.11 -m venv .venv

.PHONY: reqs
reqs:
	python3.11 -m pip install --upgrade -r requirements.txt
