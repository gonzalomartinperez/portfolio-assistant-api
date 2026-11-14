import {
  academicDocuments,
  academicEntry,
  highlightedCourseIds,
  localizedCurriculum,
} from "../academic-catalogue";
import { certificateFiles } from "../site-config";
import type { Credential, EvidenceLink, Metric, Ranking } from "../types";

export const degree = {
  qualification: "Ingeniero en Sistemas de Información",
  institution: "Universidad Nacional del Sur",
  institutionShort: "UNS",
  institutionHref: "https://www.uns.edu.ar/",
  location: "Bahía Blanca, Argentina",
  period: "Ene 2020 – Oct 2025",
  status: "Graduado",
  programme: "Una carrera de ingeniería acreditada de cinco años.",
};

export const academicResults: Metric[] = [
  {
    value: "8,67 / 10",
    label: "promedio",
    qualifier: "Sobre la carrera completa, en la escala argentina de 1 a 10.",
  },
  {
    value: "34 / 34",
    label: "materias obligatorias aprobadas",
    qualifier: "Todas las materias del plan, sin asignaturas pendientes.",
  },
  {
    value: "10 / 10",
    label: "proyecto final",
    qualifier: "Filomena, calificado con la nota máxima.",
  },
];

export const coursework = highlightedCourseIds.map((id) => academicEntry(id).name.es);

export const professionalPractice = {
  title: "Práctica Profesional Supervisada",
  detail: "Completada en agosto de 2025 como requisito de la carrera.",
};

/**
 * Los rankings son contexto institucional, nunca evidencia de desempeño individual. Cada uno
 * lleva su edición, porque una posición sin edición no es una afirmación verificable.
 */
export const rankings: Ranking[] = [
  {
    position: "#10 nacional",
    source: "SCImago Institutions Rankings",
    edition: "Edición 2026",
    href: "https://www.scimagoir.com/rankings.php?country=ARG&ranking=Overall&sector=Higher+educ.",
  },
  {
    position: "#8 nacional",
    source: "CWUR",
    edition: "Cinco ediciones consecutivas: 2020–21, 2021–22, 2022–23, 2023 y 2024",
    href: "https://cwur.org/2024/national-university-of-the-south.php",
  },
];

export const rankingCaveat =
  "Las posiciones institucionales se presentan con su ranking y edición.";

export const credentials: Credential[] = [
  {
    title: "Fundamentos de Docker",
    issuer: "Universidad Nacional del Sur",
    date: "Mar 2024",
    evidence: certificateFiles.docker,
  },
  {
    title: "Professional Power Skills",
    issuer: "Kognité",
    date: "Jun 2026",
    evidence: certificateFiles.powerSkills,
  },
];

export const credentialNote =
  "Formación completada en fundamentos de contenedores y habilidades profesionales.";

export const academicEvidence: EvidenceLink[] = [
  {
    label: "Analítico completo · PDF",
    href: academicDocuments.transcript.href,
    description: "Registro histórico emitido el 22 de diciembre de 2025",
  },
  {
    label: "Plan universitario 2012 · PDF",
    href: academicDocuments.plan.href,
    description: "Plan oficial de Ingeniería en Sistemas de Información",
  },
];

export const languageNote =
  "Inglés: comunicación profesional general (B2). La carrera incluyó además dos evaluaciones universitarias de inglés.";

/**
 * The complete degree programme, taken from the university's published plan. It is the
 * curriculum, not a transcript: no grades appear here, and none are implied.
 */
export const curriculum = localizedCurriculum("es");

export const curriculumNote =
  "Plan 2012: nombres oficiales, ubicación curricular y resultados del analítico. El año indica la ubicación en el plan, no el año de cursado. AP significa aprobado sin nota numérica.";
