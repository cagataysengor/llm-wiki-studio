import type { Metadata } from "next";

import "@/app/globals.css";
import { Sidebar } from "@/components/sidebar";

export const metadata: Metadata = {
  title: "LLM Wiki Studio",
  description: "Professional MVP frontend for a document-to-wiki AI workspace.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <div className="shell">
          <div className="dashboard-grid">
            <Sidebar />
            <main className="content">{children}</main>
          </div>
        </div>
      </body>
    </html>
  );
}

