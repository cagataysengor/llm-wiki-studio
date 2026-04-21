"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/", label: "Overview", kicker: "Workspace summary" },
  { href: "/documents", label: "Documents", kicker: "Ingest sources" },
  { href: "/wiki", label: "Wiki", kicker: "Browse knowledge" },
  { href: "/ask", label: "Ask AI", kicker: "Grounded answers" },
  { href: "/settings", label: "Settings", kicker: "Runtime config" },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-mark">LW</div>
        <div className="brand-copy">
          <span className="eyebrow">Open Source App</span>
          <h1>LLM Wiki Studio</h1>
          <p className="muted">
            A workspace for turning documents and code files into searchable knowledge.
          </p>
        </div>
      </div>

      <nav>
        {links.map((link) => (
          <Link
            className={`nav-link${pathname === link.href ? " active" : ""}`}
            href={link.href}
            key={link.href}
          >
            <span className="nav-link-text">{link.label}</span>
            <span className="nav-link-kicker">{link.kicker}</span>
          </Link>
        ))}
      </nav>

      <div className="sidebar-foot">
        <strong>Knowledge workflow</strong>
        <p className="muted">
          Upload sources, ask grounded questions, and save useful answers into the wiki.
        </p>
      </div>
    </aside>
  );
}
