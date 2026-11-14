import { technologyNames } from "../technologies";
import type { EvidenceLink, Metric, Project } from "../types";

export const filomena: Project = {
  slug: "filomena",
  name: "Filomena",
  tagline: "Exámenes de ciencias de la salud en cinco instituciones",
  period: "Ene – Dic 2025",
  summary:
    "Un monolito heredado en CakePHP y jQuery, reconstruido como una plataforma API-first que " +
    "hoy ejecuta exámenes de alta exigencia en cinco instituciones nacionales argentinas.",
  attribution:
    "Desarrollada por un equipo de tres personas. Fui el autor y contribuidor principal en " +
    "arquitectura, backend, frontend, infraestructura, seguridad, observabilidad y " +
    "coordinación. La plataforma es un logro del equipo.",
  metrics: [
    {
      value: "5",
      label: "instituciones en producción",
      qualifier: "UNS, UNRN, UNC, UNVM y FAMFyG.",
    },
    {
      value: "1.000+",
      label: "usuarios simultáneos",
      qualifier:
        "Observados en producción con consistencia completa de datos, no en un benchmark sintético.",
    },
    {
      value: "<300 ms",
      label: "endpoints críticos",
      qualifier: "Latencia promedio, mediante SQL tuning, caché Redis y colas.",
    },
    {
      value: "10 / 10",
      label: "proyecto final",
      qualifier: "Calificado en la Universidad Nacional del Sur.",
    },
  ],
  stack: technologyNames([
    "PHP",
    "Laravel",
    "React",
    "Next.js",
    "TypeScript",
    "MySQL",
    "Redis",
    "Docker",
    "GitHub Actions",
    "Prometheus",
    "Grafana",
  ]),
  links: [
    {
      label: "Contexto académico",
      href: "/es/education",
      description: "Carrera, proyecto final y registro académico",
    },
    {
      label: "Código del backend",
      href: "https://github.com/gonzalomartinperez/filomena-backend",
      description: "API REST en Laravel, en GitHub",
    },
    {
      label: "Código del frontend",
      href: "https://github.com/gonzalomartinperez/filomena-frontend",
      description: "Aplicación Next.js en GitHub",
    },
  ],
};

export const projects: Project[] = [filomena];

type CaseStudySection = {
  heading: string;
  body: readonly string[];
};

type ArchitectureStep = {
  layer: string;
  detail: string;
};

type Change = {
  aspect: string;
  before: string;
  after: string;
};

export const filomenaCaseStudy = {
  overview: {
    heading: "Una plataforma para todo el ciclo de evaluación",
    body: [
      "Filomena permite preparar, programar, tomar y corregir exámenes en instituciones de ciencias de la salud. Los administradores configuran los exámenes y el acceso, los estudiantes resuelven casos clínicos y los evaluadores corrigen las respuestas con rúbricas estructuradas.",
      "El producto reúne esos flujos, separa los datos de cada institución y protege la identidad del estudiante durante la corrección. La demostración de 43 pantallas recorre las tareas de cada rol dentro de la aplicación.",
    ],
  } satisfies CaseStudySection,

  problem: {
    heading: "El problema",
    body: [
      "Las carreras de ciencias de la salud evalúan a sus estudiantes con exámenes escritos " +
        "masivos y de alta exigencia. La primera versión de Filomena era un monolito CakePHP y " +
        "jQuery construido para una sola institución. Su rendimiento " +
        "se degradaba bajo carga concurrente, la toma de exámenes era secuencial, el control de " +
        "acceso se aplicaba de forma inconsistente y sumar una institución implicaba escribir " +
        "código.",
      "La plataforma original carecía de monitoreo proactivo. La reconstrucción incorporó visibilidad sobre el rendimiento de la aplicación y los servicios que sostienen los exámenes.",
    ],
  } satisfies CaseStudySection,

  audience: {
    heading: "Para quién es",
    body: [
      "Tres roles con necesidades genuinamente distintas. Los administradores configuran " +
        "instituciones, cursos y cronogramas. Los evaluadores redactan preguntas y revisan " +
        "resultados. Los estudiantes rinden los exámenes — y deben permanecer anónimos ante el " +
        "evaluador que los califica.",
      "Esos roles no son mutuamente excluyentes. Un profesor puede ser evaluador en un curso y " +
        "administrador en otro, y por eso el manejo de roles tuvo que ser multirol desde el " +
        "principio, en lugar de un único campo en el usuario.",
    ],
  } satisfies CaseStudySection,

  role: {
    heading: "Mi contribución",
    body: [
      "Fui el autor y contribuidor principal de un equipo de tres personas para el proyecto final de la Universidad Nacional del Sur. Mi trabajo abarcó arquitectura, backend, frontend, infraestructura, seguridad, observabilidad y coordinación.",
      "Trabajamos de forma iterativa con prácticas Agile y Trello, conectando los requisitos institucionales con la implementación de un producto funcional.",
    ],
  } satisfies CaseStudySection,

  approach: {
    heading: "De monolito a producto API-first",
    body: [
      "Separamos el monolito CakePHP y jQuery en una API REST Laravel y un frontend Next.js, React y TypeScript. La API estableció un contrato común para la interfaz y los flujos entre instituciones, con validación de entradas y control de acceso por roles. El renderizado del lado del servidor resolvía la carga inicial, seguido por los flujos interactivos de la aplicación.",
      "El tuning SQL, los índices, la caché Redis y las colas sostuvieron los flujos de exámenes concurrentes. Prometheus y Grafana permitieron observar el comportamiento de la aplicación y sus servicios en producción.",
    ],
  } satisfies CaseStudySection,

  architecture: [
    {
      layer: "Cliente",
      detail: "Next.js, React y TypeScript, para administradores, evaluadores y estudiantes.",
    },
    { layer: "API", detail: "Una API REST Laravel como contrato único para cada cliente." },
    {
      layer: "Datos",
      detail: "MySQL, con diseño de índices y tuning de consultas en los caminos de examen.",
    },
    { layer: "Caché y colas", detail: "Redis para caché y para trabajo asincrónico." },
    {
      layer: "Observabilidad",
      detail: "Prometheus y Grafana sobre la base de datos, las colas y los workers.",
    },
    { layer: "Delivery", detail: "Imágenes Docker construidas y desplegadas con GitHub Actions." },
  ] satisfies ArchitectureStep[],

  decisions: [
    {
      heading: "La seudonimia como propiedad del modelo de datos",
      body: [
        "Los estudiantes son seudónimos para los evaluadores. El modelo de datos y la API aplican esa separación, manteniendo la identidad del estudiante fuera del flujo de corrección del evaluador.",
      ],
    },
    {
      heading: "Aislamiento por institución",
      body: [
        "Cada institución administra sus propios cursos, evaluadores, estudiantes, exámenes y " +
          "cronogramas, con los datos aislados entre sí. Eso fue lo que convirtió el onboarding " +
          "de una institución nueva de trabajo de desarrollo en configuración.",
      ],
    },
    {
      heading: "Verificación de roles en ambos lados",
      body: [
        "La API aplica el control de acceso basado en roles. El frontend refleja esos permisos para mostrar a cada usuario las acciones disponibles.",
      ],
    },
    {
      heading: "Visibilidad sobre producción",
      body: [
        "Prometheus y Grafana brindan visibilidad sobre el comportamiento productivo de la base de datos, Redis, las colas y los workers, con logging estructurado y health checks.",
      ],
    },
  ] satisfies CaseStudySection[],

  changes: [
    {
      aspect: "Arquitectura",
      before: "Monolito CakePHP y jQuery",
      after: "API REST Laravel con un frontend Next.js",
    },
    {
      aspect: "Concurrencia",
      before: "Toma secuencial, una sola institución",
      after: "1.000+ usuarios simultáneos, observados en producción",
    },
    {
      aspect: "Latencia",
      before: "Se degradaba bajo carga concurrente",
      after: "Endpoints críticos por debajo de 300 ms en promedio",
    },
    {
      aspect: "Onboarding",
      before: "Requería trabajo de desarrollo",
      after: "Configuración, en minutos",
    },
    {
      aspect: "Control de acceso",
      before: "Aplicado de forma inconsistente",
      after: "RBAC multirol en API y frontend",
    },
    { aspect: "Observabilidad", before: "Ninguna", after: "Prometheus y Grafana" },
  ] satisfies Change[],

  delivery: {
    heading: "Entrega y operación",
    body: [
      "El equipo de tres personas utilizó prácticas Agile y Trello para coordinar requisitos, implementación y releases.",
      "Docker y Docker Compose proporcionaron entornos contenerizados, mientras que GitHub Actions sostuvo despliegues productivos observados por debajo de quince minutos de punta a punta. Los repositorios públicos son versiones del código y no incluyen el pipeline original de despliegue.",
    ],
  } satisfies CaseStudySection,

  outcomes: {
    heading: "Resultados en producción",
    body: [
      "Filomena está activa en UNS, UNRN, UNC, UNVM y FAMFyG. La operación productiva mostró 1.000+ usuarios simultáneos con consistencia completa de datos y endpoints críticos por debajo de 300 ms en promedio, monitoreados con Prometheus y Grafana.",
      "El proyecto final recibió 10/10 en la Universidad Nacional del Sur, además de entrevistas, cobertura universitaria y menciones de autoridades académicas.",
    ],
  } satisfies CaseStudySection,

  lessons: {
    heading: "Próximas prioridades de ingeniería",
    body: [
      "En una próxima iteración priorizaría la cobertura automatizada de regresión para exámenes concurrentes y límites de permisos. Las versiones públicas contienen actualmente tests de humo del framework.",
      "También conservaría escenarios repetibles de rendimiento junto a cada release para comparar cambios futuros con el comportamiento ya observado en producción.",
    ],
  } satisfies CaseStudySection,
};

export const filomenaEvidence: EvidenceLink[] = filomena.links;

export const filomenaHighlights: Metric[] = filomena.metrics;
