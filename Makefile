.PHONY: test demo

test:
	python -m pytest -q

demo:
	python -m g97 demo_docs.jsonl search "distributed database" -k 3
