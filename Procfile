web: gunicorn app:app --log-file=- --workers=2 --timeout=60
# worker: python -m src.scheduler # Old command
worker: python src/scheduler_cli.py start # Correct CLI entry point 