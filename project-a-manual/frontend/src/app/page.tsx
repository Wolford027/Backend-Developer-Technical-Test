"use client";

import { useEffect, useRef, useState } from "react";
import { Note } from "../../types/notes";
import { getNotes, createNote, updateNote, deleteNote } from "../../lib/api";
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

export default function NotesPage() {
  const [notes, setNotes] = useState<Note[]>([]);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [pendingId, setPendingId] = useState<number | null>(null);
  const [confirmingId, setConfirmingId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const titleRef = useRef<HTMLInputElement>(null);

  async function loadNotes() {
    try {
      setNotes(await getNotes());
      setError(null);
    } catch {
      setError("Couldn't load your notes. Is the API running?");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadNotes();
  }, []);

  function resetForm() {
    setEditingId(null);
    setTitle("");
    setContent("");
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim() || saving) return;

    setSaving(true);
    try {
      if (editingId) {
        await updateNote(editingId, { title, content });
      } else {
        await createNote({ title, content });
      }
      resetForm();
      await loadNotes();
    } catch {
      setError(editingId ? "Couldn't save that change." : "Couldn't add that note.");
    } finally {
      setSaving(false);
    }
  }

  function handleEdit(note: Note) {
    setEditingId(note.id);
    setTitle(note.title);
    setContent(note.content ?? "");
    setConfirmingId(null);
    titleRef.current?.focus();
  }

  async function handleDelete(id: number) {
    setPendingId(id);
    try {
      await deleteNote(id);
      if (editingId === id) resetForm();
      setConfirmingId(null);
      await loadNotes();
    } catch {
      setError("Couldn't delete that note.");
    } finally {
      setPendingId(null);
    }
  }

  // Cmd/Ctrl+Enter submits from anywhere in the composer.
  function handleKeyDown(e: React.KeyboardEvent) {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") handleSubmit(e);
    if (e.key === "Escape" && editingId) resetForm();
  }

  return (
    <div className={styles.page}>
      <main className={styles.shell}>
        <header className={styles.header}>
          <h1 className={styles.title}>Notes</h1>
          {!loading && notes.length > 0 && (
            <span className={styles.count}>
              {notes.length} {notes.length === 1 ? "note" : "notes"}
            </span>
          )}
        </header>

        <form
          onSubmit={handleSubmit}
          onKeyDown={handleKeyDown}
          className={`${styles.composer} ${editingId ? styles.composerEditing : ""}`}
        >
          <input
            ref={titleRef}
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Title"
            aria-label="Note title"
            className={`${styles.field} ${styles.titleField}`}
          />
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="Write something down…"
            aria-label="Note content"
            rows={3}
            className={`${styles.field} ${styles.contentField}`}
          />

          <div className={styles.composerFoot}>
            <div className={styles.composerActions}>
              {editingId && (
                <button type="button" onClick={resetForm} className={`${styles.btn} ${styles.btnGhost}`}>
                  Cancel
                </button>
              )}
              <button
                type="submit"
                disabled={!title.trim() || saving}
                className={`${styles.btn} ${styles.btnPrimary}`}
              >
                {saving ? "Saving…" : editingId ? "Save changes" : "Add note"}
              </button>
            </div>
          </div>
        </form>

        {error && (
          <div role="alert" className={styles.error}>
            <span>{error}</span>
            <button onClick={() => setError(null)} className={`${styles.btn} ${styles.btnGhost}`}>
              Dismiss
            </button>
          </div>
        )}

        {loading ? (
          <ul className={styles.list} aria-busy="true" aria-label="Loading notes">
            {[0, 1, 2].map((i) => (
              <li key={i} className={styles.item}>
                <div className={styles.itemBody} style={{ width: "100%" }}>
                  <div className={`${styles.skeletonLine} ${styles.skeletonTitle}`} />
                  <div className={`${styles.skeletonLine} ${styles.skeletonText}`} />
                </div>
              </li>
            ))}
          </ul>
        ) : notes.length === 0 ? (
          <div className={styles.empty}>
            <p className={styles.emptyTitle}>Nothing written down yet</p>
            <p className={styles.emptyText}>
              Give a note a title above and it&apos;ll show up here, newest first.
            </p>
          </div>
        ) : (
          <ul className={styles.list}>
            {notes.map((note) => (
              <li
                key={note.id}
                className={`${styles.item} ${editingId === note.id ? styles.itemEditing : ""} ${
                  pendingId === note.id ? styles.itemPending : ""
                }`}
              >
                <div className={styles.itemBody}>
                  <h2 className={styles.itemTitle}>{note.title}</h2>
                  {note.content && <p className={styles.itemContent}>{note.content}</p>}
                  <p className={styles.itemMeta}>
                    {note.updated_at
                      ? `Edited ${formatRelative(note.updated_at)}`
                      : formatRelative(note.created_at)}
                  </p>
                </div>

                <div className={styles.itemActions}>
                  {confirmingId === note.id ? (
                    <>
                      <button
                        onClick={() => setConfirmingId(null)}
                        className={`${styles.btn} ${styles.btnGhost}`}
                      >
                        Keep
                      </button>
                      <button
                        onClick={() => handleDelete(note.id)}
                        className={`${styles.btn} ${styles.btnDanger}`}
                      >
                        Delete for good
                      </button>
                    </>
                  ) : (
                    <>
                      <button
                        onClick={() => handleEdit(note)}
                        className={`${styles.btn} ${styles.btnGhost}`}
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => setConfirmingId(note.id)}
                        className={`${styles.btn} ${styles.btnDanger}`}
                      >
                        Delete
                      </button>
                    </>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </main>
    </div>
  );
}
