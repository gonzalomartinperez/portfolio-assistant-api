# Provider-port cassettes

`<prompt_version_slug>/<key>.jsonl`: one `Provider.stream` result per file (ordered text
deltas plus usage), keyed by prompt version, model, reasoning effort and messages. Written
only by `RecordingCassetteProvider` (`python -m evals.harness.golden --record`), which
refuses to run without `EVAL_RECORDING=1`, `EVAL_ENVIRONMENT=eval-live`, `ALLOW_PAID_AI=true`
and a `--campaign-budget-usd` of at most 2, and stops before any call that would exceed the
DR-04 caps (USD 2 per campaign, USD 8 per month). Never edited by hand. See
[ADR013](../../docs/adrs/013-provider-port-cassettes.md).

`spend-ledger.json` maps a month (`YYYY-MM`) to the estimated USD spent on recording; it is
committed and updated by the recorder.

Status: no cassettes are committed yet. The recording campaign is paid and is parked for the
owner; until then `just eval-golden` exits 3 ("re-record required") and the pytest golden
lane skips with that reason.
