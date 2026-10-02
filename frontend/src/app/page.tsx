import { redirect } from "next/navigation";

// La raíz lleva a las organizaciones del usuario; sin sesión, esa pantalla manda al login.
export default function RootPage() {
  redirect("/o");
}
