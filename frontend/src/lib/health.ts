// Salud del backend consultada desde el servidor de Next (no desde el navegador): /health/*
// es una sonda interna, fuera del contrato OpenAPI. Solo se usa el código HTTP (sin tipos API).
export type BackendHealth = "ok" | "fail";

export async function backendHealth(
  origin = (process.env.BACKEND_ORIGIN ?? "http://127.0.0.1:8000").replace(/\/+$/, ""),
  fetcher: typeof fetch = fetch,
): Promise<BackendHealth> {
  try {
    const response = await fetcher(`${origin}/health/ready`, {
      cache: "no-store",
      signal: AbortSignal.timeout(2000),
    });
    return response.ok ? "ok" : "fail";
  } catch {
    return "fail";
  }
}
