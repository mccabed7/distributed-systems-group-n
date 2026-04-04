import { useHost } from "../context/HostContext";
import type { User } from "../types";

export function useAuthApi() {
  const { getNextHost } = useHost();

  return {
    login: async(username: string, password: string): Promise<User> => {
      const url = `http://${getNextHost()}/login`;

      const res = await fetch(url, {
        method: "POST",
        body: JSON.stringify({ username, password }),
        headers: {
          "Content-Type": "application/json",
        },
      });

      if (!res.ok) {
        throw new Error(`Login failed: ${res.status}`)
      }

      return res.json();
    }
  }
}
