export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`/api${path}`, init);
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      message = (await response.json()).detail || message;
    } catch {
      /* plain middleware response */
    }
    if (response.status === 401)
      message = "Enter your workspace access token to continue.";
    throw new Error(message);
  }
  return response.json();
}
