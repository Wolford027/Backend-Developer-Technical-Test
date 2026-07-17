"use client";

import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import { Link } from "../../types/links";
import { ApiError, createLink, getLinks } from "../../lib/api";
import * as keyStore from "../../lib/apiKeyStore";
import styles from "./page.module.css";

// The API serializes SQLite timestamps without an offset, but they are UTC.
// Left alone, the browser would read them as local time.
function parseTimestamp(value: string): Date {
  const isUtc = /(Z|[+-]\d{2}:?\d{2})$/.test(value);
  return new Date(isUtc ? value : `${value}Z`);
}

const UNITS: [Intl.RelativeTimeFormatUnit, number][] = [
  ["year", 365 * 24 * 60 * 60 * 1000],
  ["month", 30 * 24 * 60 * 60 * 1000],
  ["day", 24 * 60 * 60 * 1000],
  ["hour", 60 * 60 * 1000],
  ["minute", 60 * 1000],
];

function formatRelative(value: string): string {
  const elapsed = parseTimestamp(value).getTime() - Date.now();
  if (Number.isNaN(elapsed)) return "";
  if (Math.abs(elapsed) < 60 * 1000) return "just now";

  const rtf = new Intl.RelativeTimeFormat(undefined, { numeric: "auto" });
  for (const [unit, ms] of UNITS) {
    if (Math.abs(elapsed) >= ms) return rtf.format(Math.round(elapsed / ms), unit);
  }
  return "just now";
}

function isExpired(link: Link): boolean {
  return link.expires_at !== null && parseTimestamp(link.expires_at) <= new Date();
}

export default function ShortenerPage() {
  const apiKey = useSyncExternalStore(
    keyStore.subscribe,
    keyStore.getSnapshot,
    keyStore.getServerSnapshot
  );
  const [keyDraft, setKeyDraft] = useState("");

  const [links, setLinks] = useState<Link[]>([]);
  const [loadedKey, setLoadedKey] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [reloadToken, setReloadToken] = useState(0);

  const [url, setUrl] = useState("");
  const [ttl, setTtl] = useState("");
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [justCreated, setJustCreated] = useState<Link | null>(null);
  const [copied, setCopied] = useState<string | null>(null);

  const urlRef = useRef<HTMLInputElement>(null);

  // Derived, not stored: we're loading when there's a key whose links we
  // haven't successfully fetched yet and nothing has failed. Storing this in
  // state would mean flipping it on synchronously inside the effect below,
  // which triggers an extra render pass for a fact already implied by the
  // state we have.
  const loading = apiKey !== null && loadedKey !== apiKey && loadError === null;

  useEffect(() => {
    if (!apiKey) return;

    // Switching keys mid-flight is a real race: the slower response can land
    // last and paint one key's links under another key's session. Anything
    // resolving after cleanup is dropped.
    let cancelled = false;

    (async () => {
      try {
        const fetched = await getLinks(apiKey);
        if (cancelled) return;
        setLinks(fetched);
        setLoadError(null);
        setLoadedKey(apiKey);
      } catch (e) {
        if (cancelled) return;
        setLoadError(e instanceof ApiError ? e.message : "Couldn't load your links.");
        // A rejected key must not leave a stale list on screen implying it worked.
        if (e instanceof ApiError && e.status === 401) setLinks([]);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [apiKey, reloadToken]);

  function refresh() {
    setLoadError(null);
    setReloadToken((t) => t + 1);
  }

  function saveKey(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = keyDraft.trim();
    if (!trimmed) return;
    keyStore.setApiKey(trimmed);
    setKeyDraft("");
    setLoadError(null);
  }

  function forgetKey() {
    keyStore.clearApiKey();
    setLinks([]);
    setLoadedKey(null);
    setJustCreated(null);
    setLoadError(null);
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!apiKey || !url.trim() || saving) return;

    setSaving(true);
    setFormError(null);
    try {
      const link = await createLink(apiKey, {
        url: url.trim(),
        expires_in_days: ttl.trim() ? Number(ttl) : null,
      });
      setJustCreated(link);
      setUrl("");
      setTtl("");
      refresh();
      urlRef.current?.focus();
    } catch (e) {
      setFormError(e instanceof ApiError ? e.message : "Couldn't shorten that URL.");
    } finally {
      setSaving(false);
    }
  }

  async function copy(text: string) {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(text);
      setTimeout(() => setCopied((c) => (c === text ? null : c)), 1500);
    } catch {
      setFormError("Couldn't copy to clipboard.");
    }
  }

  // --- signed out -----------------------------------------------------------
  if (!apiKey) {
    return (
      <main className={styles.main}>
        <div className={styles.gate}>
          <h1 className={styles.title}>Shortener</h1>
          <p className={styles.lede}>
            Paste an API key to get started. Create one with{" "}
            <code className={styles.code}>python seed_key.py my-laptop</code> in the
            backend folder.
          </p>
          <form onSubmit={saveKey} className={styles.gateForm}>
            <input
              className={styles.input}
              type="password"
              value={keyDraft}
              onChange={(e) => setKeyDraft(e.target.value)}
              placeholder="API key"
              aria-label="API key"
              autoFocus
            />
            <button className={styles.primary} type="submit" disabled={!keyDraft.trim()}>
              Continue
            </button>
          </form>
          <p className={styles.note}>
            Stored in this browser only, and sent as the{" "}
            <code className={styles.code}>X-API-Key</code> header.
          </p>
        </div>
      </main>
    );
  }

  // --- signed in ------------------------------------------------------------
  return (
    <main className={styles.main}>
      <header className={styles.header}>
        <h1 className={styles.title}>Shortener</h1>
        <button className={styles.ghost} onClick={forgetKey}>
          Forget key
        </button>
      </header>

      <form onSubmit={submit} className={styles.form}>
        <div className={styles.row}>
          <input
            ref={urlRef}
            className={styles.input}
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://example.com/a-very-long-url"
            aria-label="URL to shorten"
            autoFocus
          />
          <input
            className={styles.ttl}
            value={ttl}
            onChange={(e) => setTtl(e.target.value)}
            placeholder="Expires (days)"
            aria-label="Expires in days, optional"
            inputMode="numeric"
          />
          <button
            className={styles.primary}
            type="submit"
            disabled={!url.trim() || saving}
          >
            {saving ? "Shortening…" : "Shorten"}
          </button>
        </div>
        {formError && (
          <p className={styles.error} role="alert">
            {formError}
          </p>
        )}
      </form>

      {justCreated && (
        <div className={styles.result}>
          <a
            className={styles.resultLink}
            href={justCreated.short_url}
            target="_blank"
            rel="noreferrer"
          >
            {justCreated.short_url}
          </a>
          <button className={styles.copy} onClick={() => copy(justCreated.short_url)}>
            {copied === justCreated.short_url ? "Copied" : "Copy"}
          </button>
        </div>
      )}

      <section className={styles.dash}>
        <h2 className={styles.sectionTitle}>Your links</h2>

        {loading ? (
          <p className={styles.muted}>Loading…</p>
        ) : loadError ? (
          <div className={styles.errorBox} role="alert">
            <p>{loadError}</p>
            <button className={styles.ghost} onClick={refresh}>
              Try again
            </button>
          </div>
        ) : links.length === 0 ? (
          <p className={styles.muted}>
            No links yet. Shorten one above and it&apos;ll show up here.
          </p>
        ) : (
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Short</th>
                  <th>Destination</th>
                  <th className={styles.num}>Clicks</th>
                  <th>Created</th>
                  <th>Expires</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {links.map((link) => {
                  const expired = isExpired(link);
                  return (
                    <tr key={link.code} className={expired ? styles.dead : ""}>
                      <td>
                        <a
                          className={styles.mono}
                          href={link.short_url}
                          target="_blank"
                          rel="noreferrer"
                        >
                          /{link.code}
                        </a>
                      </td>
                      <td className={styles.dest} title={link.long_url}>
                        {link.long_url}
                      </td>
                      <td className={styles.num}>{link.click_count}</td>
                      <td className={styles.muted}>{formatRelative(link.created_at)}</td>
                      <td className={styles.muted}>
                        {link.expires_at
                          ? expired
                            ? "Expired"
                            : formatRelative(link.expires_at)
                          : "Never"}
                      </td>
                      <td>
                        <button
                          className={styles.copy}
                          onClick={() => copy(link.short_url)}
                        >
                          {copied === link.short_url ? "Copied" : "Copy"}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </main>
  );
}
