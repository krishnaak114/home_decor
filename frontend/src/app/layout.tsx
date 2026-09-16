import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  variable: "--font-geist-sans",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800"],
});

export const metadata: Metadata = {
  title: "Home Decor AI — AI-Powered Interior Design",
  description:
    "Transform your rooms with AI-powered interior design. Upload a photo, get instant style analysis, product recommendations, and realistic previews.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${inter.variable} h-full antialiased dark`} suppressHydrationWarning>
      <body className="min-h-full flex flex-col bg-[#0a0a0f] text-[#f0f0f5]" suppressHydrationWarning>{children}</body>
    </html>
  );
}
