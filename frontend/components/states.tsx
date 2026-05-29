import React, { type ReactNode } from "react";

export function LoadingState({ label }: { label: string }) {
  return (
    <section className="card">
      <div className="status">{label}</div>
    </section>
  );
}

export function ErrorState({ title, message }: { title: string; message: string }) {
  return (
    <section className="card">
      <div className="status error">{title}</div>
      <p className="subtle">{message}</p>
    </section>
  );
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <section className="card stack">
      <div className="muted-box">
        <strong>{title}</strong>
        <p className="subtle">{description}</p>
      </div>
      {action ? <div>{action}</div> : null}
    </section>
  );
}
