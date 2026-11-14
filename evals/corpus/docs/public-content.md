# Public content and documentary evidence

The website is a self-contained public projection, not a mirror of a private career
workspace. Builds require only committed public source and assets. Notion and
Reactive Resume remain historical external records, not runtime dependencies.

Use [editorial guidelines](editorial-guidelines.md) for locale, claim and catalog
presentation decisions. Content imports require explicit public scope; an asset
existing on the author's computer is not permission to publish its private data.

## CV export

`src/content/cv-public.json` is generated, not independently edited. To update it,
first reconcile the approved bilingual editorial source with its verified facts,
then run the manual export with explicit local input arguments:

```sh
node scripts/export-cv.mjs <approved-editorial-json> <verified-facts-json> <reviewed-release-manifest>
```

The exporter allows identity name, public email/location, confirmed experience,
approved copy, education, skills, languages and completed credentials. It omits
phone, evidence paths, internal notes, vacancies, hidden sections and source-system
metadata. Rich text becomes escaped React text runs, not injected HTML. HTTPS links
must not include credentials or point back to external resume services.

Provenance hashes connect the public projection with its inputs and reviewed PDF
release without publishing those inputs. Stale source/facts revisions or missing
PDF review stop the export; CI checks the published PDF hashes against that release.
Reconcile changes before exporting: an allowlist/schema cannot prove
that a professional claim is true. Keep applied knowledge distinct from developing
expertise and retain metric qualifiers, team attribution and contractual titles.

CV PDF updates use the established private DOCX/PDF pipeline: reproducible DOCX,
three-page general baseline, all six rendered pages reviewed, then explicit
manifest-bound promotion. Copy only the two promoted public PDFs. No automatic
Reactive Resume synchronization or professional-platform publication takes place.

When correcting a shared metric, compare the experience page, CV projection and
PDFs before release. Keep the measurement's baseline and qualifier consistent.
Never hand-edit the generated CV JSON or substitute an unreviewed PDF to make
the outputs appear synchronized. Update the reviewed inputs and export instead.

## Documents

The explicit list in `scripts/documents.mjs` contains six authorized assets: two
CVs, two completed-course certificates, the original university plan and the original
historical transcript. `src/content/public-documents.json` records their sizes,
MIME types and SHA-256 hashes. After an approved asset update:

```sh
node scripts/documents.mjs --write
npm run test:documents
```

Review the hash diff; this command records bytes, not approval. Browser tests check
the served response against the same manifest. No PDF viewers, preload requests,
private roadmaps or additional personal documents are part of the website.

CV download URLs carry the corresponding manifest hash through `resumeDownloads`.
Preserve that cache key when updating documents: a successful deploy can coexist
with a stale response at an unversioned CDN URL. Verify bytes using the actual
download links rendered on the live CV and Contact pages.

The transcript is explicitly authorized in original, unredacted form. Its six-month
administrative validity has expired; the page describes the issue date and historical
status. Academic outcomes remain historical facts. Original Spanish names, course
codes and placements follow the 2012 version-1 plan; English labels are translations.

See [academic reconciliation](verification/academic-evidence.md) and
[content migration](verification/content-migration.md) for source decisions.

## Release boundary

Validate content, hashes, all localized routes, visible documents and both themes.
Only task PRs integrate into develop, and only develop can promote to main. Hostinger
deploys main through its native integration. Verify live document hashes after the
deployment; a green GitHub build alone is not proof of a successful hosting release.
