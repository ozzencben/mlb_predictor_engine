import type { Metadata, Viewport } from "next"; // Viewport'u import et
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

// METADATA KISMI (Sende zaten vardır)
export const metadata: Metadata = {
  title: "Tyler's Value Hunter",
  description: "MLB Predictive Engine",
};

// 🚨 ASIL ÇÖZÜM BURASI: Tarayıcıya "Ekran dışına taşma ve zoom yapma" diyoruz
export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={inter.className}>{children}</body>
    </html>
  );
}