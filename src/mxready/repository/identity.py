from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from urllib.parse import urlsplit

from mxready.errors import MxReadyError

RepositoryProvider = str

_DEFAULT_PROVIDERS: dict[str, str] = {
    "github.com": "github",
    "gitee.com": "gitee",
}
_PATH_SEGMENT = re.compile(r"[A-Za-z0-9_.-]+")
_GIT_REF = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]*")


def build_providers(allowed_hosts: Sequence[str]) -> dict[str, str]:
    """把白名单主机名映射为 provider 标识，保持默认主机的简短名称。"""
    providers: dict[str, str] = {}
    for host in allowed_hosts:
        host = host.strip()
        if not host:
            continue
        providers[host] = _DEFAULT_PROVIDERS.get(host, host)
    return providers


@dataclass(frozen=True, slots=True)
class RepositoryIdentity:
    provider: RepositoryProvider
    owner: str
    name: str
    clone_url: str


def parse_repository_url(
    value: str,
    providers: Mapping[str, str] | None = None,
) -> RepositoryIdentity:
    """Parse a public repository URL into a safe identity.

    `providers` 缺省使用内置白名单（github.com / gitee.com），
    内部部署时可传入自定义白名单（见 `build_providers`）。
    """
    resolved_providers = _DEFAULT_PROVIDERS if providers is None else dict(providers)
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or not value.startswith("https://")
        or any(ord(character) < 32 for character in value)
    ):
        raise _invalid_repository_url()

    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError as error:
        raise _invalid_repository_url() from error

    if (
        parsed.scheme != "https"
        or parsed.username is not None
        or parsed.password is not None
        or port is not None
        or parsed.query
        or parsed.fragment
    ):
        raise _invalid_repository_url()

    host = parsed.hostname
    if host not in resolved_providers:
        raise MxReadyError(
            "UNSUPPORTED_REPOSITORY_HOST",
            "目前只支持 GitHub 和 Gitee 的公开仓库。",
        )
    if parsed.netloc != host:
        raise _invalid_repository_url()

    path = parsed.path
    if not path.startswith("/") or path.startswith("//"):
        raise _invalid_repository_url()
    path = path[1:]
    if path.endswith("/"):
        path = path[:-1]
    parts = path.split("/")
    if len(parts) != 2:
        raise _invalid_repository_url()

    owner, repository = parts
    name = repository.removesuffix(".git")
    if (
        not _is_valid_path_segment(owner)
        or not _is_valid_path_segment(name)
        or repository != name
        and repository != f"{name}.git"
    ):
        raise _invalid_repository_url()

    return RepositoryIdentity(
        provider=resolved_providers[host],
        owner=owner,
        name=name,
        clone_url=f"https://{host}/{owner}/{name}.git",
    )


def validate_git_ref(value: str | None) -> str | None:
    """Accept only bounded branch, tag, or hexadecimal commit references."""
    if value is None:
        return None
    if (
        not isinstance(value, str)
        or not 1 <= len(value) <= 200
        or _GIT_REF.fullmatch(value) is None
        or ".." in value
        or "@{" in value
        or "\\" in value
        or value.startswith("-")
        or value.endswith("/")
    ):
        raise MxReadyError(
            "INVALID_GIT_REF",
            "Git 分支、标签或提交编号格式无效。",
        )
    return value


def _is_valid_path_segment(value: str) -> bool:
    return value not in {".", ".."} and _PATH_SEGMENT.fullmatch(value) is not None


def _invalid_repository_url() -> MxReadyError:
    return MxReadyError(
        "INVALID_REPOSITORY_URL",
        "请输入完整的 GitHub 或 Gitee 公开仓库 HTTPS 地址。",
    )
