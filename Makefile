# Convenience targets (macOS/Linux). On Windows run the python commands directly.
PY ?= python

film:            ## whole pipeline, cached stages skipped
	$(PY) pipeline/run.py

shot:            ## regenerate one shot: make shot ID=s04
	$(PY) pipeline/run.py --shot $(ID)

validate:        ## check storyboard.json against the schema
	$(PY) -m pipeline.storyboard

selftest:        ## logger/cache/retry self-test (no API keys needed)
	$(PY) -m pipeline.common --selftest

.PHONY: film shot validate selftest
