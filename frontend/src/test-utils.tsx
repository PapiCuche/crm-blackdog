import { render } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import type { ReactElement } from "react";

import messages from "../messages/es-PE.json";

export function renderIntl(ui: ReactElement) {
  return render(
    <NextIntlClientProvider locale="es-PE" messages={messages} timeZone="America/Lima">
      {ui}
    </NextIntlClientProvider>,
  );
}
