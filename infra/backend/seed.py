from __future__ import annotations

import os
import time

import psycopg


def main() -> None:
    database_url = os.environ["DATABASE_URL"]
    retries = int(os.getenv("SEED_RETRIES", "10"))
    delay_seconds = float(os.getenv("SEED_RETRY_DELAY_SECONDS", "2"))

    last_error: Exception | None = None
    for _ in range(retries):
        try:
            with psycopg.connect(database_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS infra_bootstrap_state (
                            id SERIAL PRIMARY KEY,
                            name TEXT NOT NULL UNIQUE,
                            seeded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                        )
                        """
                    )
                    cur.execute(
                        """
                        INSERT INTO infra_bootstrap_state (name)
                        VALUES (%s)
                        ON CONFLICT (name) DO UPDATE
                        SET seeded_at = NOW()
                        """,
                        ("infra_seed",),
                    )
                conn.commit()
            print("Infra seed completed successfully.")
            return
        except Exception as exc:  # pragma: no cover - retry loop
            last_error = exc
            time.sleep(delay_seconds)

    raise SystemExit(f"Infra seed failed: {last_error}")


if __name__ == "__main__":
    main()
