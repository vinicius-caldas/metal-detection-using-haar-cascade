import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Haar Impurity Inspector",
  description: "Detecção de impurezas em metais raros com classificadores Haar Cascade",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  );
}
