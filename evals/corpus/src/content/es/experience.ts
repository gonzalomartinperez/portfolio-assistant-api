import { technologyNames } from "../technologies";
import type { Role } from "../types";

export const roles: Role[] = [
  {
    slug: "rampy",
    company: "Rampy",
    companyHref: "https://rampyapp.com/",
    position: "AI Engineer",
    period: "Sep 2026 – Actualidad",
    startedOn: "2026-09-01",
    location: "Estados Unidos",
    arrangement: "Remote",
    context:
      "Productos financieros e IA en una startup de ritmo alto: convierto prioridades cambiantes en funcionalidades en producción para agentes conversacionales, web, aplicaciones móviles y backend, en colaboración directa con tres fundadores.",
    contributions: [
      "Construí una vista consolidada del portfolio con activos, vaults y rendimientos de las últimas 24 horas; reduje la recuperación de datos en consultas comparables de vaults, mercados y perpetuos del rango de segundos al de milisegundos mediante precarga, consultas paralelas y caché selectiva.",
      "Mejoré los flujos agénticos mediante recuperación de contexto, reranking, salidas estructuradas y memoria conversacional selectiva; reduje contexto redundante y llamadas innecesarias, con pruebas de recorridos completos y selección de herramientas.",
      "Integré Morpho, Aave y Compound de punta a punta —backend, frontend y ejecución de transacciones— para consultar posiciones y rendimientos, depositar y retirar, con chequeos de completitud y seguimiento de estado mediante webhooks.",
      "Refactoricé límites de la aplicación y componentes reutilizables, implementé un sistema de diseño compartido y desarrollé funcionalidades móviles con React Native y Kotlin, verificadas en emuladores y teléfonos reales.",
      "Reduje el tiempo promedio de arranque de la app móvil e instrumenté recorridos clave con Microsoft Clarity y Firebase Analytics; coordiné Meta App Events y Singular SDK para evitar eventos duplicados.",
      "Diseñé, desarrollé, probé y desplegué una landing page para campañas de marketing orientadas a aumentar las descargas de la aplicación móvil.",
      "Reduje el tiempo del pipeline de validación, build y despliegue conservando sus controles; optimicé bundles, imágenes Docker y entornos de desarrollo, staging y producción en DigitalOcean.",
      "Centralicé secretos con Infisical, acceso por usuario, sincronización automatizada y rotación a demanda; trabajé sobre despliegues, monitoreo, backups, bases de datos y permisos de servidores.",
      "Preparé infraestructura escalable con el objetivo de soportar miles de usuarios, organizando entornos, contenedores y controles operativos para acompañar el crecimiento del producto.",
      "Estandaricé el desarrollo guiado por especificaciones mediante un marketplace de skills para agentes y un setup local reproducible, conectando requisitos, arquitectura, implementación, pruebas automatizadas y revisión humana de UI.",
      "Incorporé controles de dominio y frente a instrucciones maliciosas en los flujos agénticos, verificados con pruebas automatizadas de comportamiento y revisión humana.",
    ],
    attribution:
      "Ingeniería de producto desde los requisitos hasta producción, en colaboración directa con los fundadores y sobre el trabajo previo del equipo.",
    stack: technologyNames([
      "Python",
      "FastAPI",
      "Agno",
      "RAG",
      "Mem0",
      "pgvector",
      "TypeScript",
      "React",
      "Next.js",
      "React Native",
      "Kotlin",
      "Microsoft Clarity",
      "Firebase Analytics",
      "Meta App Events",
      "Singular SDK",
      "PostgreSQL",
      "Redis",
      "Celery",
      "Docker",
      "DigitalOcean",
      "Infisical",
    ]),
    metrics: [
      {
        value: "~7–8 s → 1–2 s",
        label: "arranque promedio de la app móvil",
        qualifier:
          "Promedios medidos por Gonzalo antes y después para el arranque; no se conservan la muestra ni el período de prueba y la cifra no describe todas las pantallas.",
      },
      {
        value: "~2×+",
        label: "respuestas más rápidas en flujos agénticos optimizados",
        qualifier:
          "Tiempo de respuesta estimado de aproximadamente la mitad o menos que antes en condiciones comparables; no es un benchmark de todo el sistema.",
      },
      {
        value: "~1 h → 10 min",
        label: "pipeline de entrega",
        qualifier:
          "Comparación aproximada observada para validación, build y despliegue, conservando los controles.",
      },
      {
        value: "~30%",
        label: "menos tokens en consultas optimizadas",
        qualifier:
          "Estimación para consultas afectadas por llamadas innecesarias y contexto redundante; no es un benchmark de todo el sistema.",
      },
    ],
  },
  {
    slug: "teamcubation",
    company: "Teamcubation",
    companyHref: "https://teamcubation.com/",
    position: "Software Engineer",
    period: "Dic 2025 – Ago 2026",
    startedOn: "2025-12-01",
    location: "Argentina",
    arrangement: "Remote",
    context:
      "La plataforma de promociones de Payway, una fintech líder en América Latina, al servicio " +
      "de un ecosistema de 350.000+ comercios, 70+ emisores de tarjetas y 13 países.",
    contributions: [
      "Entregué la experiencia de promociones de punta a punta: un microfrontend React y TypeScript con Single-SPA embebido como sección nativa del portal de comercios, conectado mediante un BFF Spring WebFlux a múltiples microservicios y proveedores.",
      "Diseñé un asistente RAG y agéntico integrado al producto para dueños de comercios con Python, LangChain, LangGraph, PostgreSQL/pgvector y guardrails, recuperando las promociones bancarias asociadas a cada comercio para fundamentar las respuestas del modelo.",
      "Integré el portal HTTPS de comercios con los servicios HTTP internos de la empresa mediante Amazon API Gateway.",
      "Construí microservicios en Java/Spring Boot y TypeScript/Node.js/NestJS para ingerir, normalizar y procesar promociones de comercios, entidades financieras y proveedores, adaptando los contratos según cada integración.",
      "Implementé un flujo event-driven y serverless con Amazon S3, SQS y una Lambda en Python/FastAPI con estrategias de procesamiento ordenado.",
      "Construí un entorno agéntico de ingeniería adaptado al proyecto para preservar contexto entre repositorios de integración y mantener consistencia en la entrega de funcionalidades.",
      "Apliqué arquitectura hexagonal en microservicios específicos y arquitectura en capas en otros componentes.",
      "Construí tooling en Python y Node.js para reejecutar cargas masivas de forma segura contra bases de datos locales aisladas, reconciliar resultados y exponer promociones fallidas y casos borde antes de cada release.",
    ],
    attribution:
      "Contribuidor clave de ingeniería, con responsabilidad sustancial sobre componentes dentro del equipo. Desarrollo, configuración, observabilidad y diagnóstico de aplicaciones en Docker y Kubernetes.",
    stack: technologyNames([
      "Java",
      "Spring Boot",
      "Spring WebFlux",
      "TypeScript",
      "Node.js",
      "NestJS",
      "Python",
      "FastAPI",
      "React",
      "Single-SPA",
      "PostgreSQL",
      "pgvector",
      "LangChain",
      "LangGraph",
      "AWS Lambda",
      "Amazon API Gateway",
      "Amazon S3",
      "Amazon SQS",
      "Docker",
      "Kubernetes",
      "OpenTelemetry",
      "GitLab CI/CD",
    ]),
    metrics: [
      {
        value: "20M+",
        label: "promociones cargadas",
        qualifier:
          "La carga histórica completa, ejecutada en producción, seguida de miles de promociones nuevas por día.",
      },
      {
        value: "Cero",
        label: "pérdida de datos",
        qualifier: "Validado sobre esa misma carga productiva completa.",
      },
    ],
  },
  {
    slug: "independent",
    company: "Independiente",
    links: [{ label: "Pequeverso — sitio del cliente", href: "https://pequeverso.com/" }],
    position: "AI Engineer & Full-Stack Developer",
    period: "Ene 2024 – Actualidad",
    startedOn: "2024-01-01",
    location: "Argentina",
    arrangement: "Remote",
    context:
      "Desarrollo independiente de productos mediante proyectos ocasionales para clientes de comercio electrónico, redes sociales y productos digitales.",
    contributions: [
      "Diseñé y entregué productos digitales, backoffices y extensiones de stock y punto de venta, conectando necesidades comerciales con sistemas mantenibles.",
      "Entregué la tienda de productos digitales de Pequeverso con Node.js y Next.js en Hostinger, incluyendo un asistente conversacional de compras que responde consultas sobre productos sin ejecutar compras.",
      "Construí pipelines y agentes con MCP, Claude y otros LLMs que investigan, generan y publican contenido de punta a punta.",
      "Desarrollé tiendas online, soluciones WordPress, APIs e integraciones full-stack a medida, con tooling en Python y Node.js para automatización, carga masiva y análisis de datos bajo spec-driven development.",
    ],
    attribution:
      "Entrega independiente para clientes particulares. Las cifras reúnen proyectos históricos de distintos clientes, no solo Pequeverso.",
    stack: technologyNames([
      "Python",
      "Node.js",
      "TypeScript",
      "Claude API",
      "Model Context Protocol",
      "REST APIs",
      "WordPress",
      "Next.js",
      "React",
      "Hostinger",
    ]),
    metrics: [
      {
        value: "USD 10.000+",
        label: "ganancias acumuladas para clientes",
        qualifier:
          "Ganancias generadas para los clientes por los productos entregados — no ingresos propios.",
      },
      {
        value: "≥70%",
        label: "reducción de costos operativos",
        qualifier: "Estimado por los propios clientes. No es una medición financiera auditada.",
      },
    ],
  },
  {
    slug: "cooperativa-obrera",
    company: "Cooperativa Obrera",
    companyHref: "https://www.cooperativaobrera.coop/",
    position: "Software Engineer",
    period: "Dic 2024 – Dic 2025",
    startedOn: "2024-12-01",
    location: "Bahía Blanca, Argentina",
    arrangement: "On-site",
    context:
      "Sistema de Gestión de Permisos para personal administrativo autorizado, administradores de sistemas y gerentes de la mayor cooperativa de consumo de Argentina: 150+ sucursales, 2,7M+ " +
      "asociados y un ecosistema de 50+ sistemas internos.",
    contributions: [
      "Tuve un rol principal de diseño, arquitectura e implementación, con responsabilidad sobre el desarrollo integral del producto.",
      "Construí un frontend responsive en Next.js y TypeScript cuya única interfaz era un BFF en Python/FastAPI, que definía el contrato común y desacoplaba la experiencia web de cada servicio downstream.",
      "Integré personalmente 10+ sistemas mediante microservicios Java/Spring Boot o TypeScript/Node.js/NestJS, con un contrato común de permisos y lógica interna encapsulada; las aplicaciones PHP heredadas se incorporaron mediante integraciones dedicadas.",
      "Construí un entorno agéntico personal de ingeniería cross-system para preservar contexto y trabajar en paralelo entre repositorios de integración independientes.",
      "Estandaricé el onboarding de nuevos sistemas con estructuras y filtros reutilizables.",
      "Automaticé cargas masivas y validación de datos con Python; combiné autenticación LDAP, acceso por roles y reportes de auditoría con MySQL, MariaDB y Redis. El equipo de desarrollo web continuó el mantenimiento después de mi salida.",
    ],
    attribution:
      "Responsabilidad principal de diseño e implementación del Sistema de Gestión de Permisos y sus integraciones.",
    stack: technologyNames([
      "Python",
      "FastAPI",
      "Next.js",
      "React",
      "TypeScript",
      "Java",
      "Spring Boot",
      "Node.js",
      "NestJS",
      "SQL",
      "Docker",
      "LDAP",
      "RBAC",
      "MySQL",
      "MariaDB",
      "Redis",
      "Prometheus",
      "Grafana",
      "GitLab CI/CD",
    ]),
    metrics: [
      {
        value: "10+",
        label: "sistemas integrados",
        qualifier:
          "Los sistemas alcanzados por el backoffice de permisos, integrados personalmente, dentro de un ecosistema de 50+.",
      },
      {
        value: "≥80%",
        label: "menos tickets de permisos",
        qualifier:
          "Comparado con tickets y logs antes y después del onboarding estandarizado; ≥95% de los bugs recurrentes de asignación eliminados.",
      },
      {
        value: "10 min → <10 s",
        label: "de búsqueda manual a consulta automatizada",
        qualifier:
          "Reemplacé búsquedas manuales de unos diez minutos por un flujo automatizado en el backoffice, reduciendo pasos manuales mediante la arquitectura y sus integraciones. Por separado, los endpoints críticos promediaron menos de 300 ms en pruebas repetibles on-premise, con SQL tuning, índices y paginación.",
      },
    ],
  },
];
