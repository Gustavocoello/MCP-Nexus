// src/components/layout/Clerk/ClerkLayout.jsx
import React from "react";

export default function ClerkLayout({ children }) {
  return (
    <div
      style={{
        width: "100vw",
        height: "100vh",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        background: "var(--bg)",
        overflow: "hidden",
      }}
    >
      {children}
    </div>
  );
}
