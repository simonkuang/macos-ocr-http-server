#!/bin/sh

uvicorn macos_ocr_http_service:app --host 0.0.0.0 --port 8000 --reload

