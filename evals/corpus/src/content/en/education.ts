import {
  academicDocuments,
  academicEntry,
  highlightedCourseIds,
  localizedCurriculum,
} from "../academic-catalogue";
import { certificateFiles } from "../site-config";
import type { Credential, EvidenceLink, Metric, Ranking } from "../types";

export const degree = {
  qualification: "Information Systems Engineer",
  institution: "Universidad Nacional del Sur",
  institutionShort: "UNS",
  institutionHref: "https://www.uns.edu.ar/",
  location: "Bahía Blanca, Argentina",
  period: "Jan 2020 – Oct 2025",
  status: "Graduated",
  programme: "A five-year accredited engineering program.",
};

export const academicResults: Metric[] = [
  {
    value: "8.67 / 10",
    label: "average grade",
    qualifier: "Across the full degree, on the Argentine 1–10 scale.",
  },
  {
    value: "34 / 34",
    label: "required courses passed",
    qualifier: "Every course in the program, with no outstanding subjects.",
  },
  {
    value: "10 / 10",
    label: "final-year project",
    qualifier: "Filomena, graded at the highest grade.",
  },
];

export const coursework = highlightedCourseIds.map((id) => academicEntry(id).name.en);

export const professionalPractice = {
  title: "Supervised Professional Practice",
  detail: "Completed in August 2025 as a degree requirement.",
};

/**
 * Rankings are institutional context, never evidence of individual performance. Each one
 * carries its edition, because a position without an edition is not a verifiable claim.
 */
export const rankings: Ranking[] = [
  {
    position: "#10 nationally",
    source: "SCImago Institutions Rankings",
    edition: "2026 edition",
    href: "https://www.scimagoir.com/rankings.php?country=ARG&ranking=Overall&sector=Higher+educ.",
  },
  {
    position: "#8 nationally",
    source: "CWUR",
    edition: "Five consecutive editions: 2020–21, 2021–22, 2022–23, 2023 and 2024",
    href: "https://cwur.org/2024/national-university-of-the-south.php",
  },
];

export const rankingCaveat = "Institutional positions are shown with their ranking and edition.";

export const credentials: Credential[] = [
  {
    title: "Docker Fundamentals",
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
  "Completed training in container fundamentals and professional collaboration.";

export const academicEvidence: EvidenceLink[] = [
  {
    label: "Full academic transcript · PDF",
    href: academicDocuments.transcript.href,
    description: "Historical record issued on 22 December 2025",
  },
  {
    label: "University Plan 2012 · PDF",
    href: academicDocuments.plan.href,
    description: "Official Information Systems Engineering curriculum",
  },
];

export const languageNote =
  "English: professional working proficiency (B2). The degree also included two university English examinations.";

/**
 * The complete degree program, taken from the university's published plan. It is the
 * curriculum, not a transcript: no grades appear here, and none are implied.
 */
export const curriculum = localizedCurriculum("en");

export const curriculumNote =
  "Plan 2012: curriculum placement and documented transcript results. Year refers to the curriculum, not the calendar year attended. English course names are editorial translations; original Spanish names remain available. AP means passed without a numerical grade.";
