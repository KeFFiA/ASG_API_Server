from apscheduler.job import Job
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from Config import setup_logger

logger = setup_logger(
    'scheduler_main',
    log_format='%(levelname)s:     [%(name)s] %(asctime)s | %(message)s'
)


class Scheduler:
    def __init__(self, jobs: list[dict]):
        self.scheduler = AsyncIOScheduler()
        self.jobs: list[dict] = jobs
        self.started: bool = False
        self._init_jobs()

    def start(self) -> bool:
        if not self.started:
            self.scheduler.start()
            self.started = True
            logger.info("Scheduler started")
            return self.started
        else:
            return False

    def stop(self) -> bool:
        self.scheduler.shutdown()
        self.started = False
        logger.info("Scheduler stopped")
        return self.started

    def add_job(self, job: dict):
        self.jobs.append(job)
        self.scheduler.add_job(**job)
        logger.info(f'Added job {job.get("name")}')

    def get_jobs(self) -> list[Job]:
        return self.scheduler.get_jobs()

    def _init_jobs(self):
        try:
            if len(self.jobs) != 0:
                for job in self.jobs:
                    job_name = job.get("name")
                    self.scheduler.add_job(**job)
            logger.info("Added {} jobs".format(len(self.jobs)))
        except Exception as _ex:
            logger.warning(
                "Failed to add job {} \n Error: {}".format(job_name if 'job_name' in locals() else "unknown", _ex)
            )


__all__ = ["Scheduler"]
