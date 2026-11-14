# M1-5: API image size breakdown (2026-11-14)

Master plan roadmap M1-5, input to M1-4 (canonical Dockerfile, size budget at most
500 MB as a ratchet, `ci-cd.md` section 7.2). Measured on a GitHub-hosted
`ubuntu-24.04` runner. The image is `portfolio-assistant-api:ci`, built from
`infra/docker/app/Dockerfile` at `develop` plus the M1-1 branch; M1-1 does not
change the image content. Run
[43549618795](https://github.com/gonzalomartinperez/portfolio-assistant-api/actions/runs/43549618795),
job "Container verification", step "Image size spike" (throwaway PR #149, not
merged). Sizes are uncompressed bytes as reported by `docker image inspect` and
`docker history`.

## Totals

| Item | Size |
|---|---|
| Image (`docker image inspect .Size`) | **662.5 MB** (662,471,893 B) |
| `/app/.venv` layer | 434 MB |
| Runtime apt layer (`git` plus pinned security packages) | 104 MB |
| Debian trixie base (`debian.sh`) | 78.8 MB |
| Python 3.14.8 build layer | 37.1 MB |
| pip/ensurepip removal layer | 4.3 MB |
| `app`, `contracts`, `migrations`, notices | 0.5 MB |

The audit's 992 MB figure predates PR #141 and #142.

## Site-packages (434.2 MB), top entries

| Package | Bytes | Share of site-packages |
|---|---|---|
| `lingua` | 305,925,221 | 70.5% |
| `zstandard` | 22,776,443 | 5.2% |
| `openai` | 18,288,509 | 4.2% |
| `psycopg_binary.libs` + `psycopg_binary` | 19,920,043 | 4.6% |
| `langsmith` | 7,574,226 | 1.7% |
| `pydantic_core` | 5,445,887 | 1.3% |
| `langchain_core` | 5,341,606 | 1.2% |
| everything else | about 49 MB | 11% |

`lingua` is one native extension, `lingua.cpython-314-x86_64-linux-gnu.so`
(305,897,144 bytes), with every language model compiled in. The wheel has no
per-language data files, so **the detector cannot be slimmed by restricting
languages** at install time. Restricting languages at runtime
(`LanguageDetectorBuilder.from_languages`) saves memory, not image size.

## Conclusions for M1-4

1. The plan's hypothesis holds: lingua is the dominant layer, about 306 MB of 662 MB (46% of the image).
2. Removing `git` from the `api` target (planned: `git` only in the `worker` target) saves up to about 100 MB of the 104 MB apt layer. The pinned security packages stay.
3. The expected `api` image after M1-4 is about 560 MB with lingua and about 255 MB without. **The 500 MB budget cannot be met while lingua 2.2.0 stays a dependency.**
4. Per the plan, M1-4 either:
   - accepts the measured size: set the `image.json` ratchet at the measured M1-4 value and record it in ADR 0017; or
   - replaces the detector only if golden language items stay at 100% (the golden set lands in M2-4).

   The first option is the default until the golden set exists. Replacing the detector is a dependency change that needs its own ADR.
