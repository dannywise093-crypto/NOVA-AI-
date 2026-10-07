import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "NOVA AI — Intelligence, amplified",
  description: "A next-generation AI workspace for thinking, research, and creation.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
