// import.meta.env fonctionne avec Vite sans requérir la variable au build
export const apiBase =
  (import.meta.env.PUBLIC_API_BASE_URL as string | undefined) ?? '/api';
