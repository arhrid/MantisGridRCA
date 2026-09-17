PYTHON ?= python
DATASET ?= data/Market-cloudbed-1
OUT ?= out/dev
AGENT ?= agents.telemetry_routed
N ?= 2

.PHONY: validate dev score cost compare docker clean

validate:
	$(PYTHON) run.py --dataset $(DATASET) --queries $(DATASET)/dev/query_dev.csv --out $(OUT) --agent $(AGENT) --limit $(N)
	$(PYTHON) scripts/validate_submission.py --queries $(DATASET)/dev/query_dev.csv --out $(OUT) --limit $(N)

dev:
	$(PYTHON) run.py --dataset $(DATASET) --queries $(DATASET)/dev/query_dev.csv --out $(OUT) --agent $(AGENT) --limit $(N)

score:
	$(PYTHON) score.py --predictions $(OUT)/predictions.csv --queries $(DATASET)/dev/query_dev.csv

cost:
	$(PYTHON) cost.py $(OUT)/usage.jsonl

compare:
	$(PYTHON) scripts/compare_runs.py --queries $(DATASET)/dev/query_dev.csv --out $(OUT)

docker:
	docker build -t mantisgrid-rca .
	docker run --rm -e FEATHERLESS_API_KEY -e FEATHERLESS_BASE_URL -v "$$(pwd)/$(DATASET):/data:ro" -v "$$(pwd)/out/docker:/out" mantisgrid-rca python run.py --dataset /data --queries /data/dev/query_dev.csv --out /out --limit $(N)

clean:
	rm -rf out
