/**
 * The API key, held in localStorage and exposed as an external store.
 *
 * Reading localStorage in an effect and calling setState would work, but it
 * flashes the signed-out view for one paint before the key loads, and React
 * flags the cascading render. useSyncExternalStore is the supported way to
 * read a non-React data source: getServerSnapshot covers the prerender, and
 * React swaps to the client snapshot after hydration without a mismatch.
 *
 * The `storage` event only fires in *other* tabs, so local writes notify
 * listeners explicitly. That also means signing out in one tab signs out the
 * rest, which is what someone clicking "Forget key" expects.
 */

const STORAGE_KEY = "shortener.apiKey";

const listeners = new Set<() => void>();

function emit() {
  for (const listener of listeners) listener();
}

function onStorage(event: StorageEvent) {
  if (event.key === STORAGE_KEY || event.key === null) emit();
}

export function subscribe(listener: () => void): () => void {
  if (listeners.size === 0) window.addEventListener("storage", onStorage);
  listeners.add(listener);

  return () => {
    listeners.delete(listener);
    if (listeners.size === 0) window.removeEventListener("storage", onStorage);
  };
}

export function getSnapshot(): string | null {
  return window.localStorage.getItem(STORAGE_KEY);
}

/** No localStorage during prerender; nobody is signed in on the server. */
export function getServerSnapshot(): string | null {
  return null;
}

export function setApiKey(key: string): void {
  window.localStorage.setItem(STORAGE_KEY, key);
  emit();
}

export function clearApiKey(): void {
  window.localStorage.removeItem(STORAGE_KEY);
  emit();
}
