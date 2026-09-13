# Emergency backend build, 2026-09-13 — see DECISIONS.md #7a.
FROM python:3.12-slim

WORKDIR /srv

COPY api/requirements.txt ./api/requirements.txt
RUN pip install --no-cache-dir -r api/requirements.txt

COPY api ./api
COPY auth ./auth
COPY db ./db

ENV PYTHONPATH=/srv
EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
