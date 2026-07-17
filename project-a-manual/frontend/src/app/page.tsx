"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "../../lib/api";
import styles from "./page.module.css";

type HealthResponse = { status: string };

export default function Home() {
  const [status, setStatus] = useState<"loading" | "ok" | "error">("loading");

  useEffect(() => {
    apiFetch<HealthResponse>("/api/health")
      .then(() => setStatus("ok"))
      .catch(() => setStatus("error"));
  }, []);

  return (
    <div className={styles.page}>
      <main className={styles.main}>
        <h1>Project A</h1>
        <p>
          Backend status:{" "}
          {status === "loading" && "checking..."}
          {status === "ok" && "✅ connected"}
          {status === "error" &&
            "❌ could not reach backend (is uvicorn running on :8000?)"}
        </p>
      </main>
    </div>
  );
}