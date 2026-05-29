from __future__ import annotations

import logging
import os
import time

from redis import Redis


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def main() -> None:
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    sleep_seconds = float(os.getenv("WORKER_SLEEP_SECONDS", "30"))
    client = Redis.from_url(redis_url)

    while True:
        try:
            client.ping()
            logging.info("worker heartbeat ok")
        except Exception as exc:  # pragma: no cover - runtime visibility
            logging.warning("worker heartbeat failed: %s", exc)
        time.sleep(sleep_seconds)


if __name__ == "__main__":
    main()
