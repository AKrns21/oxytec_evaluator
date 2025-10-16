import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Oxytec Feasibility Platform",
  description: "Automated feasibility studies for VOC treatment systems",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
          <nav className="border-b bg-white/80 backdrop-blur-sm">
            <div className="container mx-auto px-4 py-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-4">
                  <h1 className="text-2xl font-bold text-primary">Oxytec</h1>
                  <span className="text-sm text-muted-foreground">
                    Feasibility Platform
                  </span>
                </div>
                <div className="flex items-center space-x-4">
                  <a
                    href="/"
                    className="text-sm font-medium transition-colors hover:text-primary"
                  >
                    New Study
                  </a>
                  <a
                    href="http://localhost:8000/docs"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-muted-foreground transition-colors hover:text-primary"
                  >
                    API Docs
                  </a>
                </div>
              </div>
            </div>
          </nav>
          <main className="container mx-auto px-4 py-8">{children}</main>
        </div>
      </body>
    </html>
  );
}
