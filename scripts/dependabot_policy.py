"""Conservative decisions over authenticated GitHub data, without executing PR code."""

import copy
import re
import tomllib
from dataclasses import dataclass
from urllib.parse import urlsplit

REPOSITORY = 'gonzalomartinperez/portfolio-assistant-api'
BOT_ID = 49699333
ACTIONS_ID = 15368
POLICY_CHECK = 'Dependency policy'
# Test-only packages; compiler, framework, provider and storage updates stay manual.
PATCH = frozenset({'pytest', 'iniconfig'})
MINOR = frozenset({'iniconfig'})
FILES = frozenset({'uv.lock', 'pyproject.toml'})


@dataclass(frozen=True)
class Decision:
    eligible: bool
    reason: str
    updates: tuple[str, ...] = ()


def is_dependabot(user: dict) -> bool:
    """Require GitHub's authenticated bot account, not display text or labels."""
    return (
        user.get('login') == 'dependabot[bot]'
        and user.get('id') == BOT_ID
        and user.get('type') == 'Bot'
    )


def allowed_version(name: str, before: str, after: str) -> bool:
    """Reject unknown/zero-major, prerelease, post/local, downgrade and major versions."""
    if name not in PATCH or not all(
        re.fullmatch(r'[1-9]\d*\.\d+\.\d+', value) for value in (before, after)
    ):
        return False
    old, new = (tuple(map(int, value.split('.'))) for value in (before, after))
    return old < new and old[0] == new[0] and (old[1] == new[1] or name in MINOR)


def _manifest_versions(before: dict, after: dict) -> dict:
    """Mask only approved version constraints; all other manifest semantics must match."""
    changes = {}
    left, right = copy.deepcopy(before), copy.deepcopy(after)
    old_dev = left['dependency-groups']['dev']
    new_dev = right['dependency-groups']['dev']
    if len(old_dev) != len(new_dev):
        raise ValueError('manifest_scope')
    for index, (old, new) in enumerate(zip(old_dev, new_dev, strict=True)):
        if old == new:
            continue
        old_match = re.fullmatch(r'([a-z]+)(>=|==)(\d+\.\d+\.\d+)', old)
        new_match = re.fullmatch(r'([a-z]+)(>=|==)(\d+\.\d+\.\d+)', new)
        if (
            not old_match
            or not new_match
            or old_match.group(1, 2) != new_match.group(1, 2)
            or not allowed_version(old_match[1], old_match[3], new_match[3])
        ):
            raise ValueError('manifest_scope')
        name = old_match[1]
        changes[name] = (old_match[2] + old_match[3], new_match[2] + new_match[3])
        old_dev[index] = new_dev[index] = name
    if left != right:
        raise ValueError('manifest_scope')
    return changes


def _artifacts_valid(package: dict) -> bool:
    artifacts = [package.get('sdist', {}), *package.get('wheels', [])]
    if len(artifacts) < 2:
        return False
    for artifact in artifacts:
        if set(artifact) - {'url', 'hash', 'size', 'upload-time'}:
            return False
        url = urlsplit(artifact.get('url', ''))
        filename = url.path.rsplit('/', 1)[-1]
        prefix = f'{package["name"]}-{package["version"]}'
        if (
            url.scheme != 'https'
            or url.netloc != 'files.pythonhosted.org'
            or url.query
            or url.fragment
            or not (filename.startswith(prefix + '-') or filename == prefix + '.tar.gz')
            or not re.fullmatch(r'sha256:[0-9a-f]{64}', artifact.get('hash', ''))
            or not isinstance(artifact.get('size'), int)
            or artifact['size'] <= 0
        ):
            return False
    return True


def _runtime_names(packages: dict, root: str) -> set[str]:
    """Conservatively include all optional runtime edges, regardless of marker/platform."""
    result = set()
    pending = [item['name'] for item in packages[root].get('dependencies', [])]
    while pending:
        name = pending.pop()
        if name in result:
            continue
        result.add(name)
        package = packages[name]
        pending.extend(item['name'] for item in package.get('dependencies', []))
        for items in package.get('optional-dependencies', {}).values():
            pending.extend(item['name'] for item in items)
    return result


def dependency_changes(before: dict[str, str], after: dict[str, str]) -> Decision:
    """Compare the entire uv resolution and manifest; ambiguous impact stays manual."""
    try:
        old_manifest, new_manifest = (
            tomllib.loads(files['pyproject.toml']) for files in (before, after)
        )
        constraints = _manifest_versions(old_manifest, new_manifest)
        old_lock, new_lock = (
            tomllib.loads(files['uv.lock']) for files in (before, after)
        )
        old_list, new_list = old_lock.pop('package'), new_lock.pop('package')
        old = {package['name']: package for package in old_list}
        new = {package['name']: package for package in new_list}
        if (
            old_lock != new_lock
            or old.keys() != new.keys()
            or len(old) != len(old_list)
            or len(new) != len(new_list)
        ):
            return Decision(False, 'resolution_scope')
        root = old_manifest['project']['name']
        runtime = _runtime_names(old, root) | _runtime_names(new, root)
        updates = []
        for name, package in old.items():
            left, right = copy.deepcopy(package), copy.deepcopy(new[name])
            if name == root:
                for package, position in ((left, 0), (right, 1)):
                    for item in (
                        package.get('metadata', {})
                        .get('requires-dev', {})
                        .get('dev', [])
                    ):
                        if item['name'] in constraints:
                            if item['specifier'] != constraints[item['name']][position]:
                                return Decision(False, 'manifest_lock_mismatch')
                            item['specifier'] = 'approved-constraint'
            if left == right:
                continue
            if (
                name in runtime
                or not allowed_version(name, left['version'], right['version'])
                or left.get('source') != {'registry': 'https://pypi.org/simple'}
                or right.get('source') != left.get('source')
                or not _artifacts_valid(right)
            ):
                return Decision(False, 'unapproved_update')
            for key in ('version', 'sdist', 'wheels'):
                left.pop(key, None)
                right.pop(key, None)
            if left != right:
                return Decision(False, 'dependency_edges_changed')
            updates.append(name)
        if not updates or not constraints.keys() <= set(updates):
            return Decision(False, 'ambiguous_or_empty_update')
        for name, (_, requirement) in constraints.items():
            if not requirement.endswith(new[name]['version']):
                return Decision(False, 'manifest_lock_mismatch')
        return Decision(True, 'approved_versions', tuple(sorted(updates)))
    except (KeyError, TypeError, ValueError, AttributeError):
        return Decision(False, 'unverifiable_metadata')


def candidate(pr: dict, commits: list[dict], files: list[dict]) -> Decision:
    """Validate every authenticated commit and file before reading dependency payloads."""
    if not is_dependabot(pr.get('user', {})):
        return Decision(False, 'not_dependabot')
    if (
        pr.get('base', {}).get('ref') != 'develop'
        or pr.get('base', {}).get('repo', {}).get('full_name') != REPOSITORY
        or pr.get('head', {}).get('repo', {}).get('full_name') != REPOSITORY
    ):
        return Decision(False, 'wrong_branch_or_repository')
    if pr.get('state') != 'open' or pr.get('draft'):
        return Decision(False, 'not_open_ready')
    if any(
        label.get('name') == 'dependencies:manual' for label in pr.get('labels', [])
    ):
        return Decision(False, 'manual_opt_out')
    if (
        not commits
        or len(commits) != pr.get('commits')
        or commits[-1].get('sha') != pr['head']['sha']
        or any(
            not is_dependabot(commit.get('author') or {})
            or (commit.get('committer') or {}).get('id') != 19864447
            or not commit.get('commit', {}).get('verification', {}).get('verified')
            for commit in commits
        )
    ):
        return Decision(False, 'human_or_unverified_commit')
    if (
        not files
        or len(files) != pr.get('changed_files')
        or not {item.get('filename') for item in files} <= FILES
        or 'uv.lock' not in {item.get('filename') for item in files}
        or any(item.get('status') != 'modified' for item in files)
    ):
        return Decision(False, 'unexpected_files')
    return Decision(True, 'verified_candidate')


def protected_for_automation(repository: dict) -> bool:
    """Fail closed unless native strict checks and this trusted policy are authoritative."""
    rule = repository.get('ref', {}).get('branchProtectionRule') or {}
    required = {
        (item['context'], (item.get('app') or {}).get('databaseId'))
        for item in rule.get('requiredStatusChecks', [])
    }
    return bool(
        repository.get('autoMergeAllowed')
        and rule.get('isAdminEnforced')
        and rule.get('requiresStatusChecks')
        and rule.get('requiresStrictStatusChecks')
        and rule.get('allowsForcePushes') is False
        and rule.get('allowsDeletions') is False
        and {('checks', ACTIONS_ID), (POLICY_CHECK, ACTIONS_ID)} <= required
    )


def checks_passed(checks: list[dict], required: list[dict], sha: str) -> bool:
    """Missing, pending, failed, cancelled or ambiguous checks never authorize arming."""
    if not any(item.get('context') != POLICY_CHECK for item in required):
        return False
    for item in required:
        if item['context'] == POLICY_CHECK:
            continue
        if not (item.get('app') or {}).get('databaseId'):
            return False
        matches = [
            check
            for check in checks
            if check.get('name') == item['context']
            and check.get('head_sha') == sha
            and (check.get('app') or {}).get('id')
            == (item.get('app') or {}).get('databaseId')
        ]
        if (
            len(matches) != 1
            or matches[0].get('conclusion') != 'success'
            or matches[0].get('status') != 'completed'
        ):
            return False
    return True
