"use client";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/", icon: "🏠", text: "Check eligibility" },
  { href: "/dashboard", icon: "📋", text: "My dashboard" },
];
// Not in the student menu: the curator page is for the ScholarFit team (link in the footer of the sidebar).

export default function Nav() {
  const path = usePathname();
  return (
    <nav>
      {LINKS.map(l => (
        <a key={l.href} href={l.href} className={`navlink ${path === l.href ? "active" : ""}`}>
          <span className="ico">{l.icon}</span>{l.text}
        </a>
      ))}
    </nav>
  );
}
