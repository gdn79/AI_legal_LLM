import type { Metadata } from "next";
import "./globals.css";
import { AppProviders } from "../components/providers";

export const metadata: Metadata = {
  title: "Legal Claim AI",
  description: "Frontend MVP for local legal case workbench.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ru">
      <body>
        <AppProviders>{children}</AppProviders>
      </body>
    </html>
  );
}
