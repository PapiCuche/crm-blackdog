// Demo visual (UI-01): textos y datos ficticios del Figma GOOD DOGGY. Deterministas, sin API
// ni persistencia: cualquier cambio vive en memoria y se pierde al recargar.

export const DEMO_HOME = "/demo";
export const WORKSPACE_HOME = "/demo/workspace";

export const MODULES = [
  {
    slug: "resumen",
    label: "Resumen",
    title: "Tu negocio, en perspectiva.",
    subtitle: "Buen día, Andrea. Así se mueve tu equipo hoy.",
  },
  {
    slug: "inbox",
    label: "Inbox",
    title: "Inbox",
    subtitle: "Conversaciones que se convierten en oportunidades.",
  },
  {
    slug: "contactos",
    label: "Contactos",
    title: "Contactos",
    subtitle: "Cada cliente, una historia completa.",
  },
  {
    slug: "pipeline",
    label: "Pipeline",
    title: "Pipeline",
    subtitle: "Cada oportunidad, un paso más cerca.",
  },
  {
    slug: "cotizaciones",
    label: "Cotizaciones",
    title: "Cotizaciones",
    subtitle: "De una buena conversación a una propuesta clara.",
  },
  {
    slug: "ventas",
    label: "Ventas",
    title: "Ventas",
    subtitle: "Las oportunidades que se convirtieron en resultados.",
  },
  {
    slug: "tareas",
    label: "Tareas",
    title: "Tareas",
    subtitle: "El próximo paso, siempre a la vista.",
  },
  {
    slug: "catalogo",
    label: "Catálogo",
    title: "Catálogo",
    subtitle: "Tu catálogo, organizado hasta el último detalle.",
  },
  {
    slug: "precios",
    label: "Precios",
    title: "Precios",
    subtitle: "Listas, vigencias y promociones en un solo lugar.",
  },
  {
    slug: "inventario",
    label: "Inventario",
    title: "Inventario",
    subtitle: "Visibilidad del stock por variante y almacén.",
  },
  {
    slug: "agentes-ia",
    label: "Agentes IA",
    title: "Agentes IA",
    subtitle: "Asistencia con evidencia y aprobación humana.",
  },
  {
    slug: "canales",
    label: "Canales",
    title: "Canales",
    subtitle: "Todas las conversaciones, un mismo espacio.",
  },
  {
    slug: "automatizaciones",
    label: "Automatizaciones",
    title: "Automatizaciones",
    subtitle: "Diseña seguimientos consistentes.",
  },
  {
    slug: "reportes",
    label: "Reportes",
    title: "Reportes",
    subtitle: "Resultados claros para tomar mejores decisiones.",
  },
  {
    slug: "configuracion",
    label: "Configuración",
    title: "Configuración",
    subtitle: "Un espacio de trabajo a la medida de tu equipo.",
  },
] as const;

export type ModuleSlug = (typeof MODULES)[number]["slug"];
export type DemoModule = (typeof MODULES)[number];

export function moduleHref(slug: ModuleSlug): string {
  return slug === "resumen" ? WORKSPACE_HOME : `${WORKSPACE_HOME}/${slug}`;
}

export function findModule(slug: string): DemoModule | undefined {
  return MODULES.find((module) => module.slug === slug);
}

export const STAGES = ["Nuevo", "Calificado", "Cotización", "Negociación", "Ganada"] as const;
export type Stage = (typeof STAGES)[number];

export type Contact = {
  id: string;
  name: string;
  initials: string;
  interest: string;
  value: number;
  stage: Stage;
};

export const CONTACTS: readonly Contact[] = [
  {
    id: "camila-torres",
    name: "Camila Torres",
    initials: "CT",
    interest: "Consultoría de estrategia",
    value: 4899,
    stage: "Nuevo",
  },
  {
    id: "diego-mendoza",
    name: "Diego Mendoza",
    initials: "DM",
    interest: "Plan profesional anual",
    value: 5299,
    stage: "Calificado",
  },
  {
    id: "valeria-rojas",
    name: "Valeria Rojas",
    initials: "VR",
    interest: "Servicio de onboarding",
    value: 899,
    stage: "Cotización",
  },
  {
    id: "mateo-silva",
    name: "Mateo Silva",
    initials: "MS",
    interest: "Licencia de equipo",
    value: 2899,
    stage: "Negociación",
  },
  {
    id: "lucia-vega",
    name: "Lucía Vega",
    initials: "LV",
    interest: "Paquete de soporte",
    value: 1699,
    stage: "Ganada",
  },
];

export function usd(value: number): string {
  return `USD ${value.toLocaleString("en-US")}`;
}

export const KPIS = [
  { label: "Ventas del mes", short: "Ventas del mes", value: "USD 48,690", delta: "+18.6%" },
  { label: "Oportunidades abiertas", short: "Oportunidades", value: "32", delta: "+8" },
  { label: "Conversaciones activas", short: "Conversaciones", value: "24", delta: "92%" },
  { label: "Tasa de conversión", short: "Conversión", value: "28.4%", delta: "+4.2 pp" },
] as const;

export const WEEK_SALES = [
  { day: "Lun", value: 3200 },
  { day: "Mar", value: 5100 },
  { day: "Mié", value: 4300 },
  { day: "Jue", value: 6200 },
  { day: "Vie", value: 4800 },
  { day: "Sáb", value: 7100 },
  { day: "Dom", value: 5800 },
] as const;

const PRODUCTS = [
  ["Consultoría estratégica", "Proyecto · 4 semanas", "SRV-EST-001", "USD 4,899", "12 disponibles"],
  ["Plan profesional", "Suscripción · Anual", "PLAN-PRO-001", "USD 5,299", "8 disponibles"],
  ["Servicio de onboarding", "Servicio · Remoto", "SRV-ONB-001", "USD 899", "24 disponibles"],
  ["Licencia de equipo", "Suscripción · Mensual", "LIC-EQP-001", "USD 2,899", "3 disponibles"],
  ["Paquete de soporte", "Servicio · Premium", "SRV-SOP-001", "USD 1,699", "6 disponibles"],
] as const;

// La última columna de cada tabla se pinta como etiqueta de estado.
export type TableData = {
  columns: readonly string[];
  rows: readonly (readonly string[])[];
};

export const TABLES: Partial<Record<ModuleSlug, TableData>> = {
  contactos: {
    columns: ["Contacto", "Interés", "Valor", "Etapa"],
    rows: CONTACTS.map((c) => [c.name, c.interest, usd(c.value), c.stage]),
  },
  cotizaciones: {
    columns: ["Número", "Cliente", "Importe", "Estado"],
    rows: CONTACTS.map((c, i) => [
      `COT-00${i + 1}`,
      c.name,
      usd(c.value),
      i === 0 ? "Pendiente" : "Borrador",
    ]),
  },
  ventas: {
    columns: ["Venta", "Cliente", "Total", "Pago"],
    rows: CONTACTS.slice(2).map((c, i) => [`VEN-00${i + 1}`, c.name, usd(c.value), "Yape"]),
  },
  tareas: {
    columns: ["Tarea", "Contacto", "Responsable", "Vence"],
    rows: CONTACTS.map((c) => ["Seguimiento", c.name, "Andrea López", "Hoy · 15:00"]),
  },
  catalogo: { columns: ["Producto", "Variante", "SKU", "Precio", "Stock"], rows: PRODUCTS },
  precios: {
    columns: ["Producto", "Variante", "SKU", "Precio público", "Disponibilidad"],
    rows: PRODUCTS,
  },
  inventario: {
    columns: ["Producto", "Variante", "SKU", "Precio", "Disponible · Lima"],
    rows: PRODUCTS,
  },
  "agentes-ia": {
    columns: ["Agente", "Modelo", "Modo", "Estado"],
    rows: [
      ["Asistente comercial", "Por configurar", "Asistido", "Demo"],
      ["Soporte de productos", "Por configurar", "Sombra", "Demo"],
    ],
  },
  canales: {
    columns: ["Canal", "Cuenta", "Capacidad", "Estado"],
    rows: [
      ["Sandbox", "GOOD DOGGY Demo", "Mensajería local", "Demo"],
      ["WhatsApp", "Sin conectar", "Ventana de 24 horas", "Pendiente"],
      ["Instagram", "Sin conectar", "Fase futura", "Pendiente"],
    ],
  },
  automatizaciones: {
    columns: ["Regla", "Evento", "Acción", "Estado"],
    rows: [
      ["Seguimiento comercial", "Sin respuesta", "Crear tarea", "Borrador"],
      ["Atención humana", "Solicitud del cliente", "Transferir", "Borrador"],
    ],
  },
  configuracion: {
    columns: ["Ajuste", "Valor", "Ámbito", "Estado"],
    rows: [
      ["Organización", "GOOD DOGGY", "Demo", "Activo"],
      ["Moneda", "USD · USD", "Organización", "Activo"],
      ["Zona horaria", "UTC-5", "Organización", "Activo"],
      ["Equipo comercial", "5 miembros ficticios", "Equipo", "Demo"],
      ["Permisos y auditoría", "Por integrar", "Seguridad", "Pendiente"],
    ],
  },
};
