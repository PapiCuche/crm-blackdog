import messages from "../../messages/es-PE.json";

import { ApiError } from "./http";

export type ApiErrorKey = keyof typeof messages.errors.api;

// Un solo sitio decide qué se le dice al usuario ante un error de la API: por `code`, nunca
// por el texto que venga en la respuesta. Un código sin mensaje propio usa el genérico.
export function apiErrorKey(error: unknown): ApiErrorKey {
  if (error instanceof ApiError && Object.hasOwn(messages.errors.api, error.code)) {
    return error.code as ApiErrorKey;
  }
  return "INTERNAL_ERROR";
}
