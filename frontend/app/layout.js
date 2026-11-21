import "./globals.css";

export const metadata = { title: "ScholarFit", description: "Criterion-level scholarship eligibility checks" };

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        <header className="top">
          <a href="/" className="brand">ScholarFit</a>
          <nav><a href="/">Check eligibility</a><a href="/curator">Curator</a></nav>
        </header>
        <main>{children}</main>
        <footer>ScholarFit advises only. The official programme page is always authoritative.</footer>
      </body>
    </html>
  );
}
