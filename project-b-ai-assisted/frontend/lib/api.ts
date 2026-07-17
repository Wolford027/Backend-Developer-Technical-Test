import { Link, LinkInput } from "../types/links";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/** Thrown for any non-2xx response, carrying the status so callers can react. */
export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

/**
 * Turn a failed response into something a human can act on.
 *
 * "Something went wrong" tells the user nothing they didn't already know.
 * Each of these points at the next thing to actually do.
 */
async function toError(res: Response): Promise<ApiError> {
  let detail: string | undefined;
  try {
    const body = await res.json();
    // FastAPI sends `detail` as a string, or as an array of objects for 422.
    if (typeof body?.detail === "string") {
      detail = body.detail;
    } else if (Array.isArray(body?.detail)) {
      detail = body.detail[0]?.msg;
    }
  } catch {
    // Body wasn't JSON. Fall through to the generic messages below.
  }

  switch (res.status) {
    case 401:
      return new ApiError(401, "That API key isn't valid. Check it and try again.");
    case 404:
      return new ApiError(404, "That short link doesn't exist.");
    case 410:
      return new ApiError(410, "That short link has expired.");
    case 422:
      return new ApiError(422, detail ?? "That doesn't look like a valid URL.");
    default:
      return new ApiError(res.status, detail ?? `Request failed (${res.status}).`);
  }
}

async function request<T>(path: string, apiKey: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      ...init,
      cache: "no-store",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": apiKey,
        ...init?.headers,
      },
    });
  } catch {
    // fetch only rejects on network-level failure, so this is the one case
    // where the API isn't reachable at all -- worth saying plainly.
    throw new ApiError(0, "Can't reach the API. Is the backend running on :8000?");
  }

  if (!res.ok) throw await toError(res);
  return res.json();
}

export function getLinks(apiKey: string): Promise<Link[]> {
  return request<Link[]>("/api/links", apiKey);
}

export async function createLink(apiKey: string, data: LinkInput): Promise<Link> {
  return request<Link>("/api/links", apiKey, {
    method: "POST",
    body: JSON.stringify(data),
  });
}
