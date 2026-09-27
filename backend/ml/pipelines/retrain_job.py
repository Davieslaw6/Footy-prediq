"""
Continuous learning scheduler — runs retraining every Monday and Thursday.
"""
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("retrain_job")

def scheduled_retrain():
    from app.ml.retrain_runner import run_retrain_and_reload
    logger.info("Starting scheduled retraining run...")
    try:
        summary = run_retrain_and_reload(tune=False)
        logger.info(f"Retraining complete: {summary['training_rows']} rows, winner acc={summary['winner']['accuracy']:.3f}")
    except Exception:
        logger.exception("Scheduled retraining failed")

if __name__ == "__main__":
    scheduler = BlockingScheduler()
    scheduler.add_job(
        scheduled_retrain,
        CronTrigger(day_of_week="mon,thu", hour=6, minute=0),
        id="retrain_job",
        misfire_grace_time=3600,
    )
    logger.info("Retrain scheduler started. Waiting for Mon/Thu 06:00...")
    scheduler.start()

# Alternative plain cron:
# 0 6 * * 1,4 cd /path/to/backend && /path/to/venv/bin/python -m app.ml.retrain_runner
