"use client";

import React from "react";
import { IntegrationSettingsPage } from "../../../components/integration-settings-page";

export default function FnsSettingsPage() {
  return (
    <IntegrationSettingsPage
      title="Настройки ФНС"
      description="Backend-настройки mock/manual интеграции ФНС и readiness к будущему API."
      integrationName="fns"
      filter={(item) => item.key.toUpperCase().includes("FNS")}
    />
  );
}
