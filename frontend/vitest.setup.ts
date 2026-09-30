import "@testing-library/jest-dom/vitest";

import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

afterEach(cleanup); // sin `globals`, Testing Library no limpia el DOM entre tests
