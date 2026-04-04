import { useHost } from "../context/HostContext";
import { useAuth } from "../context/AuthContext";

export function useApiClient() {
  const { getNextHost } = useHost();
  const { user } = useAuth();

  const request = async (path: string, options?: RequestInit) => {
    const host = getNextHost();
	const url = `http://${host}${path}`

    const res = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(user?.token ? { Authorization: `Bearer ${user.token}` } : {}),
        ...options?.headers,
      },
    });

    if (!res.ok) {
      throw new Error(`Request failed: ${res.status}`);
    }

    return res.json();
  };

  return { request };
}
