"use client";

import React from "react";
import { IntegrationSettingsPage } from "../../../components/integration-settings-page";

export default function CourtArbitrSettingsPage() {
  return (
    <IntegrationSettingsPage
      integrationName="court_arbitr"
      title="Court Arbitr Settings"
      description="Backend settings for mock/manual Court Arbitr integration readiness."
      filter={(item) => item.key.toUpperCase().includes("COURT")}
    />
  );
}
