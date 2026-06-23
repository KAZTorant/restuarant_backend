import threading
from typing import Any, Dict, Optional


_lock = threading.Lock()
_pending_jobs: Dict[str, Dict[str, Any]] = {}


def register_pending_job(job_id: str) -> threading.Event:
    event = threading.Event()
    with _lock:
        _pending_jobs[job_id] = {'event': event, 'result': None}
    return event


def complete_job(job_id: str, result: dict) -> bool:
    with _lock:
        entry = _pending_jobs.get(job_id)
        if not entry:
            return False
        entry['result'] = result
        entry['event'].set()
        return True


def pop_job_result(job_id: str) -> Optional[dict]:
    with _lock:
        entry = _pending_jobs.pop(job_id, None)
    if not entry:
        return None
    return entry.get('result')


def wait_for_job(job_id: str, timeout: float) -> Optional[dict]:
    with _lock:
        entry = _pending_jobs.get(job_id)
        if not entry:
            return None
        event = entry['event']

    if not event.wait(timeout):
        with _lock:
            _pending_jobs.pop(job_id, None)
        return None

    return pop_job_result(job_id)
