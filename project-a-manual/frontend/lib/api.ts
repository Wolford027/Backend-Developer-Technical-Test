import { Note, NoteInput } from "../types/notes";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function getNotes(): Promise<Note[]> {
  const res = await fetch(`${API_URL}/notes`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch notes");
  return res.json();
}

export async function createNote(data: NoteInput): Promise<Note> {
  const res = await fetch(`${API_URL}/notes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to create note");
  return res.json();
}

export async function updateNote(id: number, data: Partial<NoteInput>): Promise<Note> {
  const res = await fetch(`${API_URL}/notes/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to update note");
  return res.json();
}

export async function deleteNote(id: number): Promise<void> {
  const res = await fetch(`${API_URL}/notes/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to delete note");
}