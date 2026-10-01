import { getRequestConfig } from "next-intl/server";

import messages from "../../messages/es-PE.json";

// Fase 1: un solo locale (es-PE); el enrutado por locale llega si se necesita otro idioma.
export const LOCALE = "es-PE";
export const TIME_ZONE = "America/Lima"; // por defecto; la zona real es la de la organización

export default getRequestConfig(async () => ({ locale: LOCALE, messages, timeZone: TIME_ZONE }));
