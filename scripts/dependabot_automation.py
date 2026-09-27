"""Trusted-base Dependabot controller. PR contents are parsed as data, never run."""

import argparse
import base64
import json
import os
import re
import subprocess
from dataclasses import asdict
from pathlib import Path

from scripts.dependabot_policy import (
    ACTIONS_ID,
    FILES,
    POLICY_CHECK,
    REPOSITORY,
    Decision,
    candidate,
    checks_passed,
    dependency_changes,
    is_dependabot,
    protected_for_automation,
)

ROOT = f'repos/{REPOSITORY}'
CONTROL_QUERY = """query {
  repository(owner:"gonzalomartinperez", name:"portfolio-assistant-api") {
    autoMergeAllowed
    ref(qualifiedName:"refs/heads/develop") {
      target { oid }
      branchProtectionRule {
        isAdminEnforced requiresStatusChecks requiresStrictStatusChecks
        allowsForcePushes allowsDeletions
        requiresApprovingReviews requiredApprovingReviewCount
        requiredStatusChecks { context app { databaseId } }
      }
    }
  }
}"""


class GitHubRequestError(RuntimeError):
    """An API failure containing only fixed endpoint/category diagnostics."""

    def __init__(self, message: str, *, permission_denied: bool = False):
        super().__init__(message)
        self.permission_denied = permission_denied


class GitHub:
    """Use gh's existing scoped authentication; never extract or print its token."""

    def request(self, path: str, method: str = 'GET', data: dict | None = None):
        command = ['gh', 'api', '--method', method, path]
        if data is not None:
            command += ['--input', '-']
        result = subprocess.run(
            command,
            input=json.dumps(data) if data is not None else None,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )
        if result.returncode:
            status = re.search(r'HTTP (\d{3})', result.stderr)
            endpoint = 'graphql' if path == 'graphql' else 'rest'
            denied = bool(status and status[1] in ('401', '403'))
            field = ''
            try:
                errors = json.loads(result.stdout).get('errors', [])
                for error in errors:
                    if error.get('type') in ('FORBIDDEN', 'INSUFFICIENT_SCOPES'):
                        denied = True
                        allowed = {
                            'repository',
                            'ref',
                            'branchProtectionRule',
                            'autoMergeAllowed',
                            'requiredStatusChecks',
                            'app',
                            'databaseId',
                        }
                        field = '.'.join(
                            part
                            for part in error.get('path', [])
                            if isinstance(part, str) and part in allowed
                        )
            except (ValueError, AttributeError, TypeError):
                pass  # Malformed error bodies are never echoed or treated as approval.
            raise GitHubRequestError(
                f'{endpoint}; HTTP {status[1] if status else "unknown"}'
                + (f'; denied field {field}' if field else ''),
                permission_denied=denied,
            )
        value = json.loads(result.stdout)
        if isinstance(value, dict) and value.get('errors'):
            raise ValueError('github_graphql_error')
        return value

    def graph(self, query: str, variables: dict | None = None):
        return self.request(
            'graphql', 'POST', {'query': query, 'variables': variables or {}}
        )['data']


def controls(api: GitHub) -> dict:
    return api.graph(CONTROL_QUERY)['repository']


def inspect_candidate(api: GitHub, pr: dict) -> Decision:
    """Bound API reads and inspect immutable file blobs, including Git file modes."""
    number = int(pr['number'])
    if pr.get('commits', 0) > 20 or pr.get('changed_files', 0) > 2:
        return Decision(False, 'change_too_large')
    commits = api.request(f'{ROOT}/pulls/{number}/commits?per_page=100')
    files = api.request(f'{ROOT}/pulls/{number}/files?per_page=100')
    decision = candidate(pr, commits, files)
    if not decision.eligible:
        return decision
    snapshots = []
    for sha in (pr['base']['sha'], pr['head']['sha']):
        if not re.fullmatch(r'[0-9a-f]{40}', sha):
            return Decision(False, 'invalid_revision')
        tree = api.request(f'{ROOT}/git/trees/{sha}')
        entries = {item['path']: item for item in tree['tree']}
        if tree.get('truncated') or any(
            entries.get(path, {}).get('mode') != '100644' for path in FILES
        ):
            return Decision(False, 'unexpected_file_mode')
        snapshot = {}
        for path in sorted(FILES):
            blob = api.request(f'{ROOT}/git/blobs/{entries[path]["sha"]}')
            if blob.get('encoding') != 'base64' or blob.get('size', 0) > 512_000:
                return Decision(False, 'unverifiable_blob')
            snapshot[path] = base64.b64decode(blob['content']).decode('utf-8')
        snapshots.append(snapshot)
    return dependency_changes(*snapshots)


def change_auto_merge(api: GitHub, pr: dict, enable: bool) -> None:
    """Only native auto-merge; never approve, push, rebase, bypass or directly merge."""
    if enable:
        query = """mutation($id: ID!) {
          enablePullRequestAutoMerge(input: {pullRequestId: $id, mergeMethod: MERGE}) {
            pullRequest { id }
          }
        }"""
    else:
        if not pr.get('auto_merge'):
            return
        query = """mutation($id: ID!) {
          disablePullRequestAutoMerge(input: {pullRequestId: $id}) {
            pullRequest { id }
          }
        }"""
    api.graph(query, {'id': pr['node_id']})


def hold_check(api: GitHub, pr: dict, manual: bool = False) -> tuple[int, bool]:
    """Place the required current-head hold before revoking or arming native auto-merge."""
    response = api.request(
        f'{ROOT}/commits/{pr["head"]["sha"]}/check-runs?filter=latest&per_page=100'
    )
    if response['total_count'] > 100:
        raise ValueError('ambiguous_checks')
    external_id = f'dependency-policy-v1:{pr["number"]}'
    matching = [
        check
        for check in response['check_runs']
        if check['name'] == POLICY_CHECK
        and check['app']['id'] == ACTIONS_ID
        and check.get('external_id') in (external_id, external_id + ':manual')
    ]
    data = {
        'status': 'in_progress',
        'output': {
            'title': 'Revalidating dependency policy',
            'summary': 'Native auto-merge remains gated by this current-head check.',
        },
    }
    # Store the current-head manual decision in trusted check metadata before any
    # later API failure. Quality reruns must not silently reverse a human opt-out.
    manual = manual or any(
        check.get('external_id') == external_id + ':manual' for check in matching
    )
    data['external_id'] = external_id + (':manual' if manual else '')
    if matching:
        if len(matching) != 1:
            raise ValueError('ambiguous_policy_check')
        check_id = matching[0]['id']
        api.request(f'{ROOT}/check-runs/{check_id}', 'PATCH', data)
        return check_id, manual
    created = api.request(
        f'{ROOT}/check-runs',
        'POST',
        {
            **data,
            'name': POLICY_CHECK,
            'head_sha': pr['head']['sha'],
            'external_id': data['external_id'],
        },
    )
    return created['id'], manual


def finish_check(api: GitHub, check_id: int, conclusion: str, reason: str) -> None:
    api.request(
        f'{ROOT}/check-runs/{check_id}',
        'PATCH',
        {
            'status': 'completed',
            'conclusion': conclusion,
            'output': {
                'title': reason,
                'summary': 'See docs/dependency-updates.md. No PR code was executed by this policy.',
            },
        },
    )


def current_candidate(pr: dict, fresh: dict, base: str) -> bool:
    """Rebase, retarget, label change or target advancement invalidates the decision."""
    return (
        fresh.get('state') == 'open'
        and fresh.get('head', {}).get('sha') == pr['head']['sha']
        and fresh.get('base', {}).get('ref') == 'develop'
        and fresh.get('base', {}).get('sha') == base == pr['base']['sha']
        and fresh.get('labels') == pr.get('labels')
        and not fresh.get('draft')
        and fresh.get('mergeable') is True
    )


def process(api: GitHub, number: int, expected_head: str, manual: bool = False) -> str:
    pr = api.request(f'{ROOT}/pulls/{number}')
    if pr['state'] != 'open' or pr['head']['sha'] != expected_head:
        return 'stale_event'
    check_id, manual = hold_check(api, pr, manual)
    if not is_dependabot(pr.get('user', {})):
        finish_check(
            api, check_id, 'success', 'Manual PR; not managed by dependency automation'
        )
        return 'not_dependabot'
    change_auto_merge(api, pr, False)
    if pr['base']['ref'] != 'develop':
        finish_check(
            api,
            check_id,
            'action_required',
            'Wrong target; automatic main merges are forbidden',
        )
        return 'wrong_target'
    if manual:
        finish_check(
            api, check_id, 'success', 'Explicit manual path; native auto-merge disabled'
        )
        return 'manual_review'
    if os.environ.get('DEPENDABOT_AUTOMERGE_ENABLED') != 'true':
        finish_check(
            api, check_id, 'success', 'Automation paused; native auto-merge disabled'
        )
        return 'paused'
    repository = controls(api)
    if not protected_for_automation(repository):
        finish_check(
            api, check_id, 'action_required', 'Missing required activation protections'
        )
        return 'unprotected'
    decision = inspect_candidate(api, pr)
    if not decision.eligible:
        finish_check(api, check_id, 'action_required', decision.reason)
        return decision.reason
    response = api.request(
        f'{ROOT}/commits/{expected_head}/check-runs?filter=latest&per_page=100'
    )
    required = repository['ref']['branchProtectionRule']['requiredStatusChecks']
    if response['total_count'] > 100 or not checks_passed(
        response['check_runs'], required, expected_head
    ):
        finish_check(
            api,
            check_id,
            'action_required',
            'Required CI is not successful; Quality completion reevaluates this head',
        )
        return 'waiting_for_required_checks'
    compare = api.request(
        f'{ROOT}/compare/{repository["ref"]["target"]["oid"]}...{expected_head}'
    )
    fresh = api.request(f'{ROOT}/pulls/{number}')
    refreshed_controls = controls(api)
    if not protected_for_automation(refreshed_controls):
        finish_check(
            api, check_id, 'action_required', 'Protection changed during evaluation'
        )
        return 'protection_changed'
    base = refreshed_controls['ref']['target']['oid']
    if (
        not current_candidate(pr, fresh, base)
        or compare['merge_base_commit']['sha'] != base
    ):
        finish_check(
            api,
            check_id,
            'action_required',
            'Revision changed, conflict or rebase required; reevaluate the current head',
        )
        return 'waiting_for_rebase_or_conflict_resolution'
    # The required policy check is still in progress. GitHub can only merge after
    # it succeeds, and still applies approvals, strict freshness and all native rules.
    change_auto_merge(api, fresh, True)
    finish_check(
        api,
        check_id,
        'success',
        'Eligible dependency update; native rules remain authoritative',
    )
    return 'native_auto_merge_enabled'


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--audit-pr', type=int)
    args = parser.parse_args()
    api = GitHub()
    if args.audit_pr:
        pr = api.request(f'{ROOT}/pulls/{args.audit_pr}')
        try:
            repository = controls(api)
        except GitHubRequestError as error:
            if not error.permission_denied:
                raise
            # This diagnostic job has no merge authority. Record the blocker rather
            # than grant it write/admin access. The privileged controller still fails
            # closed if its own protection query is unavailable.
            print(
                json.dumps(
                    {
                        'pr': args.audit_pr,
                        'head': pr['head']['sha'],
                        'eligible': False,
                        'protections_ready': False,
                        'audit_state': 'permission_blocked',
                        'reason': str(error),
                    },
                    indent=2,
                )
            )
            return
        decision = inspect_candidate(api, pr)
        print(
            json.dumps(
                {
                    'pr': args.audit_pr,
                    'head': pr['head']['sha'],
                    **asdict(decision),
                    'protections_ready': protected_for_automation(repository),
                },
                indent=2,
            )
        )
        return
    if os.environ.get('GITHUB_REPOSITORY') != REPOSITORY:
        raise ValueError('wrong_repository')
    event = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())
    kind = os.environ['GITHUB_EVENT_NAME']
    manual = False
    if kind == 'pull_request_target':
        requests = [(event['number'], event['pull_request']['head']['sha'])]
    elif kind == 'workflow_run':
        run = event['workflow_run']
        if (
            run['name'] != 'Quality'
            or run['event'] != 'pull_request'
            or run['head_repository']['full_name'] != REPOSITORY
        ):
            return
        requests = [
            (pr['number'], run['head_sha'])
            for pr in api.request(
                f'{ROOT}/commits/{run["head_sha"]}/pulls?per_page=100'
            )
            if pr['state'] == 'open' and pr['head']['sha'] == run['head_sha']
        ]
    elif kind == 'workflow_dispatch':
        if os.environ.get('GITHUB_REF') != 'refs/heads/main':
            raise ValueError('dispatch_requires_default_branch')
        actor = os.environ['GITHUB_ACTOR']
        permission = api.request(f'{ROOT}/collaborators/{actor}/permission')[
            'permission'
        ]
        if permission not in ('admin', 'maintain', 'write'):
            raise ValueError('manual_actor_not_authorized')
        inputs = event['inputs']
        manual = inputs['mode'] == 'manual'
        if inputs['mode'] not in ('manual', 'reevaluate') or not re.fullmatch(
            r'[0-9a-f]{40}', inputs['head']
        ):
            raise ValueError('invalid_dispatch')
        requests = [(int(inputs['number']), inputs['head'])]
    else:
        raise ValueError('unsupported_event')
    for number, head in requests:
        print(
            json.dumps(
                {'pr': number, 'decision': process(api, int(number), head, manual)}
            )
        )


if __name__ == '__main__':
    try:
        main()
    except GitHubRequestError as error:
        raise SystemExit(f'Dependency policy failed closed ({error}).') from None
    except (
        subprocess.SubprocessError,
        KeyError,
        TypeError,
        ValueError,
        AttributeError,
        OSError,
    ):
        # API diagnostics can contain user-controlled text. Leave the hold in place.
        raise SystemExit(
            'Dependency policy failed closed; inspect API availability and trusted configuration.'
        ) from None
