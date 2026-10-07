import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "RDF Knowledge Graph",
  description: "Semantic web knowledge graph with SPARQL, OWL reasoning, and SHACL validation",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
