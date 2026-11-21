# ADR028: Adopt the src layout and rename the application package

Status: accepted (2026-11-21, master plan task M4-4).

## Context and problem

The generic top-level package name `app` can collide with other packages in tooling.
The repository-root layout also lets imports succeed from the checkout before the project
is installed. [PAA-D10](../master-plan/README.md) adopts the src layout required by
[ecosystem section 10.2](../master-plan/ecosystem.md). vps-ops still uses the original
ASGI and operator module names.

## Decision drivers

- Give the application a distinct import name and exercise installation in normal development.
- Preserve existing operator invocations during the vps-ops transition.
- Preserve prompt content, migration SQL and the public HTTP and SSE contracts.
- Apply the dependency rules from [ADR010](010-import-linter-contracts.md) to the renamed package.

## Considered options

1. **Rename under `src/` and ship compatibility shims (chosen).** Install the application
   as `portfolio_assistant` and preserve the existing vps-ops targets during the transition.
2. **Move `app` under `src/`.** This exercises installation and retains the generic import name.
3. **Rename and remove the old targets immediately.** This requires a coordinated switch
   in vps-ops before the renamed image can be used.

## Decision outcome

Move the application to `src/portfolio_assistant`. Build both that package and a
temporary `src/app` compatibility namespace. The ASGI shim exposes the same FastAPI
instance, and the four operator shims delegate to the corresponding module entry points.

In the expand phase, keep the old targets available and document the `assistant-*`
console scripts as canonical. The owner and vps-ops must switch the scheduled commands
and API launch to those scripts and confirm the change before the contract phase can
remove `src/app`. The new package keeps only `portfolio_assistant.main` (the ASGI module);
the old module-level dispatchers live only in the `app` namespace. See the
[deployment contract](../reference/deployment-contract.md).

## Consequences

- Application imports, build inputs and tool configuration use the new package layout.
- Import Linter checks the application layers. The AST guard rejects imports of the
  compatibility namespace from the application, including its package initializer.
- The installed image supports existing vps-ops commands throughout the expand phase.

## Confirmation

- Run Import Linter and the architecture probes, including the import from the application
  into the compatibility namespace.
- Import the five compatibility modules in a fresh Python process and check that the
  ASGI shim exposes the canonical FastAPI object.
- Inspect the built wheel for both packages and regenerate the public wire artifacts
  to confirm they have no diff.
