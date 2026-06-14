// Pure client-side SPA: the app talks to the backend API at runtime and reads
// the auth token from localStorage, so there is no server rendering or
// prerendering. The static adapter emits an index.html fallback for all routes.
export const ssr = false;
export const prerender = false;
