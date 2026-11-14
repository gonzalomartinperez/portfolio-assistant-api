import { technologyNames } from "../technologies";
import type { EvidenceLink, Metric, Project } from "../types";

export const filomena: Project = {
  slug: "filomena",
  name: "Filomena",
  tagline: "Health-sciences exams across five institutions",
  period: "Jan – Dec 2025",
  summary:
    "A legacy CakePHP and jQuery monolith, rebuilt as an API-first platform that now runs " +
    "high-stakes exams for five Argentine national institutions.",
  attribution:
    "Built by a three-person team. I was the principal author and contributor across " +
    "architecture, backend, frontend, infrastructure, security, observability and coordination. " +
    "The platform is a team achievement.",
  metrics: [
    {
      value: "5",
      label: "institutions in production",
      qualifier: "UNS, UNRN, UNC, UNVM and FAMFyG.",
    },
    {
      value: "1,000+",
      label: "simultaneous users",
      qualifier:
        "Observed in production with complete data consistency, not a synthetic benchmark.",
    },
    {
      value: "<300 ms",
      label: "critical endpoints",
      qualifier: "Average latency, through SQL tuning, Redis caching and queues.",
    },
    {
      value: "10 / 10",
      label: "final-year project",
      qualifier: "Graded at Universidad Nacional del Sur.",
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
      label: "Academic context",
      href: "/education",
      description: "Degree, final project and academic record",
    },
    {
      label: "Backend source",
      href: "https://github.com/gonzalomartinperez/filomena-backend",
      description: "Laravel REST API on GitHub",
    },
    {
      label: "Frontend source",
      href: "https://github.com/gonzalomartinperez/filomena-frontend",
      description: "Next.js application on GitHub",
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
    heading: "One platform for the assessment lifecycle",
    body: [
      "Filomena supports exam preparation, scheduling, delivery and assessment for health-sciences institutions. Administrators configure exams and access, students work through clinical cases, and evaluators assess answers against structured rubrics.",
      "The product brings those workflows together while separating institutional data and protecting student identity in the assessment process. Its 43-screen demonstration below follows those roles through the application.",
    ],
  } satisfies CaseStudySection,

  problem: {
    heading: "The problem",
    body: [
      "Health-sciences degrees assess students through large, high-stakes written exams. " +
        "Filomena's first version was a CakePHP and jQuery monolith built for a single " +
        "institution. Performance degraded under concurrent " +
        "load, exam delivery was sequential, access control was enforced inconsistently, and " +
        "adding an institution meant writing code.",
      "The original platform lacked proactive monitoring. The rebuild added visibility into application performance and the services supporting exam delivery.",
    ],
  } satisfies CaseStudySection,

  audience: {
    heading: "Who it is for",
    body: [
      "Three roles with genuinely different needs. Administrators configure institutions, " +
        "courses and schedules. Evaluators author questions and review results. Students sit " +
        "the exams — and must remain anonymous to the evaluator grading them.",
      "Those roles are not mutually exclusive. A professor can be an evaluator in one course " +
        "and an administrator in another, which is why role handling had to be multi-role from " +
        "the start rather than a single field on a user.",
    ],
  } satisfies CaseStudySection,

  role: {
    heading: "My contribution",
    body: [
      "I was the principal author and contributor in a three-person final-project team at Universidad Nacional del Sur. My work covered architecture, backend, frontend, infrastructure, security, observability and coordination.",
      "We delivered iteratively with Agile practices and Trello, bringing together institutional requirements and the implementation of a working product.",
    ],
  } satisfies CaseStudySection,

  approach: {
    heading: "From monolith to API-first product",
    body: [
      "We separated the CakePHP and jQuery monolith into a Laravel REST API and a Next.js, React and TypeScript frontend. The API provided a common contract for the interface and multi-institution workflows, with input validation and role-based access control. Server-side rendering supported the initial page load, followed by interactive application flows.",
      "SQL tuning, indexes, Redis caching and queues supported concurrent exam workflows. Prometheus and Grafana made production behavior visible across the application and its supporting services.",
    ],
  } satisfies CaseStudySection,

  architecture: [
    {
      layer: "Client",
      detail: "Next.js, React and TypeScript, serving administrators, evaluators and students.",
    },
    { layer: "API", detail: "A Laravel REST API as the single contract for every client." },
    { layer: "Data", detail: "MySQL, with index design and query tuning on the exam paths." },
    { layer: "Cache and queues", detail: "Redis for caching and for asynchronous work." },
    {
      layer: "Observability",
      detail: "Prometheus and Grafana over the database, queues and workers.",
    },
    { layer: "Delivery", detail: "Docker images built and deployed through GitHub Actions." },
  ] satisfies ArchitectureStep[],

  decisions: [
    {
      heading: "Pseudonymity as a data-model property",
      body: [
        "Students are pseudonymous to evaluators. The data model and API enforce that boundary, keeping student identity separate from the evaluator's assessment workflow.",
      ],
    },
    {
      heading: "Isolation per institution",
      body: [
        "Each institution manages its own courses, evaluators, students, exams and schedules, " +
          "with data isolated between them. This is what turned onboarding a new institution " +
          "from development work into configuration.",
      ],
    },
    {
      heading: "Role checks on both sides",
      body: [
        "The API enforces role-based access control. The frontend reflects those permissions so users see the actions available to them.",
      ],
    },
    {
      heading: "Visibility into production",
      body: [
        "Prometheus and Grafana provide visibility into production behavior across the database, Redis, queues and workers, supported by structured logging and health checks.",
      ],
    },
  ] satisfies CaseStudySection[],

  changes: [
    {
      aspect: "Architecture",
      before: "CakePHP and jQuery monolith",
      after: "Laravel REST API with a Next.js frontend",
    },
    {
      aspect: "Concurrency",
      before: "Sequential, single-institution delivery",
      after: "1,000+ simultaneous users, observed in production",
    },
    {
      aspect: "Latency",
      before: "Degraded under concurrent load",
      after: "Critical endpoints below 300 ms on average",
    },
    {
      aspect: "Onboarding",
      before: "Required development work",
      after: "Configuration, in minutes",
    },
    {
      aspect: "Access control",
      before: "Inconsistently enforced",
      after: "Multi-role RBAC across API and frontend",
    },
    { aspect: "Observability", before: "None", after: "Prometheus and Grafana" },
  ] satisfies Change[],

  delivery: {
    heading: "Delivery and operation",
    body: [
      "Our three-person team used Agile practices and Trello to coordinate requirements, implementation and release.",
      "Docker and Docker Compose provided containerized environments, while GitHub Actions supported production deployments observed at under fifteen minutes end to end. The public code repositories are snapshots and do not include the original deployment pipeline.",
    ],
  } satisfies CaseStudySection,

  outcomes: {
    heading: "Production results",
    body: [
      "Filomena is active at UNS, UNRN, UNC, UNVM and FAMFyG. Production operation showed 1,000+ simultaneous users with complete data consistency and critical endpoints below 300 ms on average, monitored through Prometheus and Grafana.",
      "The final project received 10/10 at Universidad Nacional del Sur, alongside university interviews, coverage and mentions from academic authorities.",
    ],
  } satisfies CaseStudySection,

  lessons: {
    heading: "Next engineering priorities",
    body: [
      "The next iteration would prioritize automated regression coverage for concurrent exams and permission boundaries. The public snapshots currently contain framework smoke tests.",
      "I would also preserve repeatable performance scenarios alongside each release, so future changes can be compared with the production behavior already observed.",
    ],
  } satisfies CaseStudySection,
};

export const filomenaEvidence: EvidenceLink[] = filomena.links;

export const filomenaHighlights: Metric[] = filomena.metrics;
