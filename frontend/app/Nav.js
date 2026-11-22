"use client";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/", icon: "🏠", text: "Check eligibility" },
  { href: "/curator", icon: "✅", text: "Curator review" },
];

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
