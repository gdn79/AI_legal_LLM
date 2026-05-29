"use client";

import React, { type ReactNode } from "react";
import { AuthGate, ShellNav } from "./providers";

export function AppShell({
  title,
  description,
  actions,
  children,
}: {
  title: string;
  description?: string;
  actions?: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="app-shell">
      <ShellNav />
      <AuthGate>
        <main className="container">
          <div className="toolbar">
            <div>
              <h1 className="page-title">{title}</h1>
              {description ? <p className="subtle">{description}</p> : null}
            </div>
            {actions ? <div>{actions}</div> : null}
          </div>
          <div style={{ height: 24 }} />
          {children}
        </main>
      </AuthGate>
    </div>
  );
}
