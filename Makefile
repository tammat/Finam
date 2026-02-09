.PHONY: gen test

gen:
	./scripts/gen_protos.sh

test:
	python -m pytest -q