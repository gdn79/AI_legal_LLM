"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { AppShell } from "../../../components/app-shell";
import { CaseForm } from "../../../components/case-form";
import { canRole, useAuth } from "../../../components/providers";
import { EmptyState } from "../../../components/states";
import { apiClient } from "../../../lib/api-client";

export default function NewCasePage() {
  const router = useRouter();
  const { user } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  return (
    <AppShell title="Создать дело" description="Форма создания карточки дела.">
      {canRole(user, ["initiator", "admin"]) ? (
        <CaseForm
          submitting={saving}
          error={error}
          onSubmit={async (values) => {
            setSaving(true);
            setError(null);
            try {
              const created = await apiClient.createCase(values);
              router.push(`/cases/${created.id}`);
            } catch (err) {
              setError(err instanceof Error ? err.message : "Не удалось создать дело");
              setSaving(false);
            }
          }}
        />
      ) : (
        <EmptyState title="Создание дела недоступно" description="Эта форма доступна только ролям initiator и admin." />
      )}
    </AppShell>
  );
}
