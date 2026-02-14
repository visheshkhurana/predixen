#!/bin/bash
cd "$(dirname "$0")/.."
python qa-lab/runner/qa_runner.py "$@"
