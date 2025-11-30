import type { Metadata } from "next";
import { Inter, Michroma } from "next/font/google";
import "./globals.css";

const inter = Inter({ 
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const michroma = Michroma({ 
  weight: "400",
  subsets: ["latin"],
  variable: "--font-michroma",
  display: "swap",
});

export const metadata: Metadata = {
  title: "ListingLens - Property Intelligence Dashboard",
  description: "AI-powered property data extraction and analysis dashboard",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${inter.variable} ${michroma.variable} antialiased bg-slate-50 text-slate-900 font-sans`}
      >
        {children}
      </body>
    </html>
  );
}
