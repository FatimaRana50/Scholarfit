import "./globals.css";
import Nav from "./Nav";

export const metadata = { title: "ScholarFit", description: "Criterion-level scholarship eligibility checks" };

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        <div className="shell">
          <aside className="sidebar">
            <a href="/" className="logo"><span className="mark">🎓</span>ScholarFit</a>
            <Nav />
            <div className="side-note">
              <strong>ScholarFit advises only.</strong>
              The official programme page is always authoritative.
            </div>
            <a href="/curator" className="staff-link">Staff: curator sign-in</a>
          </aside>
          <main className="content">{children}</main>
        </div>
      </body>
    </html>
  );
}
