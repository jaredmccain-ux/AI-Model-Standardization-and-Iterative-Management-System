import "./globals.css";
import "antd/dist/reset.css";
import AppShell from "@/components/AppShell";

export const metadata = {
  title: "Vision model iterate hub",
  description: "Vision data annotation, training, evaluation, and continuous iteration in one platform",
};

export default function RootLayout({ children }) {
  return (
    <html lang="zh-CN">
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
