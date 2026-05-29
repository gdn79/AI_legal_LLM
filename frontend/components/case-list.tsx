import Link from "next/link";
import type { CaseSummary } from "../lib/types";

export function CaseList({ cases }: { cases: CaseSummary[] }) {
  return (
    <section className="card">
      <div className="list">
        {cases.map((item) => (
          <article className="list-item" key={item.id}>
            <div className="stack">
              <Link href={`/cases/${item.id}`}>
                <strong>{item.title}</strong>
              </Link>
              <div className="muted">
                {item.plaintiff} {"->"} {item.defendant}
              </div>
              <div className="pill-row">
                <span className="pill">{item.status}</span>
                <span className="pill">{item.amount}</span>
              </div>
            </div>
            <span className="muted">{item.updatedAt}</span>
          </article>
        ))}
      </div>
    </section>
  );
}
