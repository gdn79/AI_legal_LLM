"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { createContext, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { apiClient } from "../lib/api-client";
import type { LoginInput, Role, UserProfile } from "../lib/types";

type AuthContextValue = {
  user: UserProfile | null;
  loading: boolean;
  login: (input: LoginInput) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AppProviders({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const stored = window.localStorage.getItem("legal-claim-ai-user");
    const bootstrap = async () => {
      if (!stored) {
        setLoading(false);
        return;
      }
      try {
        setUser(JSON.parse(stored) as UserProfile);
      } catch {
        window.localStorage.removeItem("legal-claim-ai-user");
      }
      try {
        const profile = await apiClient.getMe();
        setUser(profile);
        window.localStorage.setItem("legal-claim-ai-user", JSON.stringify(profile));
      } catch {
        apiClient.logout();
        window.localStorage.removeItem("legal-claim-ai-user");
        setUser(null);
      } finally {
        setLoading(false);
      }
    };
    void bootstrap();
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      login: async (input) => {
        const profile = await apiClient.login(input);
        setUser(profile);
        window.localStorage.setItem("legal-claim-ai-user", JSON.stringify(profile));
      },
      logout: () => {
        setUser(null);
        apiClient.logout();
        window.localStorage.removeItem("legal-claim-ai-user");
      },
    }),
    [loading, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AppProviders");
  return context;
}

export function canRole(user: UserProfile | null, allowed: Role[]) {
  return !!user && allowed.includes(user.role);
}

export function AuthGate({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, router, user]);

  if (loading) return <div className="container">Loading...</div>;
  if (!user) return null;
  return <>{children}</>;
}

export function ShellNav() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const items = [
    ["/cases", "Cases", ["initiator", "lawyer", "manager", "admin"]],
    ["/organizations", "Organizations", ["lawyer", "manager", "admin"]],
    ["/pilot-feedback", "Pilot feedback", ["lawyer", "manager", "admin"]],
    ["/pilot-metrics", "Pilot metrics", ["manager", "admin"]],
    ["/court-import", "Court import", ["lawyer", "manager", "admin"]],
    ["/external-court-cases", "External cases", ["lawyer", "manager", "admin"]],
    ["/dashboard", "Dashboard", ["manager", "admin"]],
    ["/legal-sources", "RAG sources", ["initiator", "lawyer", "manager", "admin"]],
    ["/audit", "Audit", ["admin"]],
    ["/settings", "Settings", ["admin"]],
  ] as const;

  return (
    <header className="topbar">
      <div className="brand">
        <strong>Legal Claim AI</strong>
        <span>{user ? `${user.email} · ${user.role}` : "guest"}</span>
      </div>
      <nav className="nav">
        {items
          .filter(([, , allowed]) => !user || (allowed as readonly Role[]).includes(user.role))
          .map(([href, label]) => (
            <Link key={href} href={href} data-active={pathname?.startsWith(href) ? "true" : "false"}>
              {label}
            </Link>
          ))}
        {user ? (
          <button type="button" onClick={logout}>
            Logout
          </button>
        ) : (
          <Link href="/login">Login</Link>
        )}
      </nav>
    </header>
  );
}

export function RoleGuard({ allowed, children, fallback }: { allowed: Role[]; children: ReactNode; fallback?: ReactNode }) {
  const { user } = useAuth();
  if (!user || !allowed.includes(user.role)) {
    return fallback ?? <div className="status warning">Action is not available for role {user?.role ?? "guest"}.</div>;
  }
  return <>{children}</>;
}
