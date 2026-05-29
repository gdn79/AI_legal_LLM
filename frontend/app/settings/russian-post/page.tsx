"use client";

import React from "react";
import { IntegrationSettingsPage } from "../../../components/integration-settings-page";

export default function RussianPostSettingsPage() {
  return (
    <IntegrationSettingsPage
      integrationName="russian_post"
      title="Russian Post Settings"
      description="Backend settings for mock/manual Russian Post integration readiness."
      filter={(item) => item.key.toUpperCase().includes("RUSSIAN_POST")}
    />
  );
}
