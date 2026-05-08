import structlog
from datetime import datetime, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from typing import Callable

logger = structlog.get_logger(__name__)


class SchedulerService:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._jobs: dict[str, str] = {}

    def start(self) -> None:
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("scheduler started")

    def stop(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("scheduler stopped")

    def schedule_periodic_analysis(
        self, portfolio_id: int, analysis_func: Callable, interval_minutes: int = 60
    ) -> str:
        job_id = f"analysis_{portfolio_id}_{interval_minutes}m"

        if job_id in self._jobs:
            logger.info("analysis job already scheduled", job_id=job_id)
            return job_id

        self.scheduler.add_job(
            analysis_func,
            trigger=IntervalTrigger(minutes=interval_minutes),
            id=job_id,
            name=f"Periodic Analysis - Portfolio {portfolio_id}",
            replace_existing=True,
            args=[portfolio_id],
        )
        self._jobs[job_id] = f"every_{interval_minutes}_minutes"
        logger.info(
            "scheduled periodic analysis",
            portfolio_id=portfolio_id,
            interval=interval_minutes,
            job_id=job_id,
        )
        return job_id

    def schedule_daily_summary(
        self, summary_func: Callable, portfolio_id: int | None = None
    ) -> str:
        job_id = "daily_summary"
        if portfolio_id:
            job_id = f"daily_summary_{portfolio_id}"

        if job_id in self._jobs:
            logger.info("daily summary job already scheduled", job_id=job_id)
            return job_id

        self.scheduler.add_job(
            summary_func,
            trigger=CronTrigger(hour=9, minute=0),
            id=job_id,
            name="Daily Portfolio Summary",
            replace_existing=True,
            args=[portfolio_id] if portfolio_id else [],
        )
        self._jobs[job_id] = "daily_at_9am"
        logger.info("scheduled daily summary", job_id=job_id)
        return job_id

    def schedule_risk_check(
        self, risk_check_func: Callable, portfolio_id: int | None = None
    ) -> str:
        job_id = "risk_check"
        if portfolio_id:
            job_id = f"risk_check_{portfolio_id}"

        if job_id in self._jobs:
            logger.info("risk check job already scheduled", job_id=job_id)
            return job_id

        self.scheduler.add_job(
            risk_check_func,
            trigger=IntervalTrigger(minutes=15),
            id=job_id,
            name="Risk Check",
            replace_existing=True,
            args=[portfolio_id] if portfolio_id else [],
        )
        self._jobs[job_id] = "every_15_minutes"
        logger.info("scheduled risk check", job_id=job_id)
        return job_id

    def add_job(
        self,
        func: Callable,
        trigger: str = "interval",
        minutes: int = 60,
        job_id: str | None = None,
        **kwargs,
    ) -> str:
        job_id = job_id or f"job_{func.__name__}_{datetime.now(timezone.utc).timestamp()}"

        if trigger == "interval":
            trigger_obj = IntervalTrigger(minutes=minutes)
        elif trigger == "cron":
            hour = kwargs.get("hour", 9)
            minute = kwargs.get("minute", 0)
            trigger_obj = CronTrigger(hour=hour, minute=minute)
        else:
            trigger_obj = IntervalTrigger(minutes=minutes)

        self.scheduler.add_job(
            func,
            trigger=trigger_obj,
            id=job_id,
            replace_existing=True,
            **kwargs,
        )
        self._jobs[job_id] = f"{trigger}_{minutes}m" if trigger == "interval" else f"cron"
        logger.info("job added", job_id=job_id, trigger=trigger)
        return job_id

    def remove_job(self, job_id: str) -> bool:
        if job_id in self._jobs:
            try:
                self.scheduler.remove_job(job_id)
                del self._jobs[job_id]
                logger.info("job removed", job_id=job_id)
                return True
            except Exception as e:
                logger.error("failed to remove job", job_id=job_id, error=str(e))
                return False
        logger.warning("job not found", job_id=job_id)
        return False

    def get_jobs(self) -> list[dict]:
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run_time": str(job.next_run_time) if job.next_run_time else None,
                "trigger": str(job.trigger),
            })
        return jobs
