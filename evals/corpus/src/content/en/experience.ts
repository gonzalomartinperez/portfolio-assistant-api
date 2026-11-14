import { technologyNames } from "../technologies";
import type { Role } from "../types";

export const roles: Role[] = [
  {
    slug: "rampy",
    company: "Rampy",
    companyHref: "https://rampyapp.com/",
    position: "AI Engineer",
    period: "Sep 2026 – Present",
    startedOn: "2026-09-01",
    location: "United States",
    arrangement: "Remote",
    context:
      "AI and financial products in a fast-moving startup: turning evolving priorities into production features across conversational agents, web, mobile and backend services, working directly with three founders.",
    contributions: [
      "Built a consolidated portfolio experience for assets, vaults and 24-hour returns; reduced comparable vault, market and perpetual data retrieval from seconds into the millisecond range through prefetching, parallel provider calls and selective caching.",
      "Improved agent workflows through retrieval, reranking, structured outputs and selective conversational memory; reduced redundant context and unnecessary calls while testing complete user journeys and tool selection.",
      "Integrated Morpho, Aave and Compound across backend, frontend and transaction execution for positions, yields, deposits and withdrawals, with completeness checks and webhook-based status tracking.",
      "Refactored application boundaries and reusable components, delivered a shared design system, and developed mobile features with React Native and Kotlin, tested in emulators and on physical devices.",
      "Reduced average mobile app startup time and instrumented key user journeys with Microsoft Clarity and Firebase Analytics; coordinated Meta App Events and Singular SDK to avoid duplicate event reporting.",
      "Designed, built, tested and deployed a web landing page for marketing campaigns aimed at increasing mobile app downloads.",
      "Shortened the validation, build and deployment pipeline while retaining its checks; optimized application bundles, Docker images and development, staging and production environments on DigitalOcean.",
      "Centralized secrets with Infisical, per-user access, automated synchronization and on-demand rotation; worked across deployment, monitoring, backups, databases and server permissions.",
      "Prepared scalable infrastructure with the design goal of supporting thousands of users, organizing environments, containers and operational controls for product growth.",
      "Standardized spec-driven engineering through an agent skills marketplace and repeatable local setup, connecting requirements, architecture, implementation, automated tests and human UI review.",
      "Added domain and malicious-instruction controls to agent workflows, checked with automated behavioral tests and human review.",
    ],
    attribution:
      "Product engineering from requirements through production, in direct collaboration with the founders and building on the team's existing work.",
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
        label: "average mobile app startup",
        qualifier:
          "Owner-measured before/after averages for app startup; sample and test window were not retained, and the result does not describe every screen.",
      },
      {
        value: "~2×+",
        label: "faster responses in optimized agent workflows",
        qualifier:
          "Estimated response times of roughly half the previous baseline or less under comparable conditions; not a system-wide benchmark.",
      },
      {
        value: "~1 h → 10 min",
        label: "delivery pipeline",
        qualifier:
          "Approximate observed before/after for validation, build and deployment, with checks retained.",
      },
      {
        value: "~30%",
        label: "fewer tokens in targeted queries",
        qualifier:
          "Estimated reduction for queries affected by unnecessary calls and redundant context; not a system-wide benchmark.",
      },
    ],
  },
  {
    slug: "teamcubation",
    company: "Teamcubation",
    companyHref: "https://teamcubation.com/",
    position: "Software Engineer",
    period: "Dec 2025 – Aug 2026",
    startedOn: "2025-12-01",
    location: "Argentina",
    arrangement: "Remote",
    context:
      "The promotions platform for Payway, a leading Latin American fintech, serving an " +
      "ecosystem of 350,000+ merchants, 70+ card issuers and 13 countries.",
    contributions: [
      "Delivered the promotions experience end to end: a Single-SPA React and TypeScript microfrontend embedded as a native section of the merchant portal, connected through a Spring WebFlux BFF to multiple microservices and providers.",
      "Designed an in-product RAG and agentic assistant for merchant owners with Python, LangChain, LangGraph, PostgreSQL/pgvector and guardrails, retrieving the banking promotions tied to each merchant to ground the model's answers.",
      "Integrated the HTTPS merchant portal with internal HTTP enterprise services through Amazon API Gateway.",
      "Built Java/Spring Boot and TypeScript/Node.js/NestJS microservices to ingest, normalize and process promotions from merchants, financial entities and providers, adapting contracts per integration.",
      "Implemented an event-driven, serverless flow with Amazon S3, SQS and a Python/FastAPI Lambda using ordered processing strategies.",
      "Built a project-specific agentic engineering environment to preserve context across integration repositories and support consistent feature delivery.",
      "Applied hexagonal architecture in selected microservices and layered architecture in other components.",
      "Built Python and Node.js tooling to replay bulk loads safely against isolated local databases, reconcile results and surface failed promotions and edge cases before release.",
    ],
    attribution:
      "Key engineering contributor with substantial component ownership within the team. Application development, configuration, observability and diagnostics in Docker and Kubernetes environments.",
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
        label: "promotions loaded",
        qualifier:
          "The complete historical load, executed in production, followed by thousands of new promotions daily.",
      },
      {
        value: "Zero",
        label: "data loss",
        qualifier: "Validated across that same complete production load.",
      },
    ],
  },
  {
    slug: "independent",
    company: "Self-employed",
    links: [{ label: "Pequeverso — client website", href: "https://pequeverso.com/" }],
    position: "AI Engineer & Full-Stack Developer",
    period: "Jan 2024 – Present",
    startedOn: "2024-01-01",
    location: "Argentina",
    arrangement: "Remote",
    context:
      "Independent product engineering through occasional projects for clients in e-commerce, social media and digital products.",
    contributions: [
      "Designed and shipped digital products, back offices and stock and point-of-sale extensions, connecting commercial needs to maintainable systems.",
      "Delivered Pequeverso’s digital-products storefront with Node.js and Next.js on Hostinger, including a conversational shopping assistant that answers product questions without executing purchases.",
      "Built MCP-, Claude- and LLM-powered pipelines and agents that research, generate and publish content end to end.",
      "Developed online stores, WordPress solutions, APIs and custom full-stack integrations, with Python and Node.js tooling for automation, bulk processing and data analysis under spec-driven development.",
    ],
    attribution:
      "Independent delivery for individual clients. The figures below cover historical client projects collectively, not Pequeverso alone.",
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
        value: "USD 10,000+",
        label: "cumulative client profit",
        qualifier: "Profit generated for clients by the products delivered — not personal revenue.",
      },
      {
        value: "≥70%",
        label: "operating-cost reduction",
        qualifier: "Estimated by the clients themselves. Not an audited financial measurement.",
      },
    ],
  },
  {
    slug: "cooperativa-obrera",
    company: "Cooperativa Obrera",
    companyHref: "https://www.cooperativaobrera.coop/",
    position: "Software Engineer",
    period: "Dec 2024 – Dec 2025",
    startedOn: "2024-12-01",
    location: "Bahía Blanca, Argentina",
    arrangement: "On-site",
    context:
      "A permissions-management back office for authorized administrative staff, system administrators and managers at " +
      "Argentina's largest consumer cooperative: 150+ branches, 2.7M+ members and " +
      "an ecosystem of 50+ internal systems.",
    contributions: [
      "Held a principal design, architecture and implementation role with product-engineering scope.",
      "Built a responsive Next.js and TypeScript frontend whose only interface was a Python/FastAPI BFF, which defined the shared contract and decoupled the web experience from every downstream service.",
      "Personally integrated 10+ systems through Java/Spring Boot or TypeScript/Node.js/NestJS microservices, each conforming to the permissions API contract and encapsulating its own logic; legacy PHP applications used dedicated integrations.",
      "Built a personal cross-system agentic engineering environment to preserve context and work in parallel across independent integration repositories.",
      "Standardized onboarding for new systems with reusable structures and filters.",
      "Automated bulk loads and data validation with Python; combined LDAP authentication, role-based access and exportable audit reports with MySQL, MariaDB and Redis. The web development team took over maintenance after my departure.",
    ],
    attribution:
      "Principal design and implementation responsibility for the permissions-management product and its integrations.",
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
        label: "systems integrated",
        qualifier:
          "The systems within the permissions back office’s scope, integrated personally, inside an ecosystem of 50+.",
      },
      {
        value: "≥80%",
        label: "fewer permission tickets",
        qualifier:
          "Compared against tickets and logs before and after standardized onboarding; ≥95% of recurring assignment bugs eliminated.",
      },
      {
        value: "10 min → <10 s",
        label: "manual to automated permission lookup",
        qualifier:
          "Replaced a roughly ten-minute manual search with an automated back-office workflow, reducing manual steps through the system's architecture and integrations. Separately, critical endpoints averaged below 300 ms in repeatable on-premise tests, supported by SQL tuning, indexing and pagination.",
      },
    ],
  },
];
