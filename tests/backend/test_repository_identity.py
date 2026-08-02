import pytest
from mxready.errors import MxReadyError
from mxready.repository.identity import (
    build_providers,
    parse_repository_url,
    validate_git_ref,
)


@pytest.mark.parametrize(
    ("url", "provider", "owner", "name", "clone_url"),
    [
        (
            "https://github.com/pytorch/extension-cpp.git",
            "github",
            "pytorch",
            "extension-cpp",
            "https://github.com/pytorch/extension-cpp.git",
        ),
        (
            "https://gitee.com/metax-maca/cu-bridge",
            "gitee",
            "metax-maca",
            "cu-bridge",
            "https://gitee.com/metax-maca/cu-bridge.git",
        ),
    ],
)
def test_public_repository_urls_are_normalized(
    url: str,
    provider: str,
    owner: str,
    name: str,
    clone_url: str,
) -> None:
    identity = parse_repository_url(url)

    assert identity.provider == provider
    assert identity.owner == owner
    assert identity.name == name
    assert identity.clone_url == clone_url


@pytest.mark.parametrize(
    "url",
    [
        "",
        "http://github.com/pytorch/extension-cpp",
        "HTTPS://github.com/pytorch/extension-cpp",
        "https://user:token@github.com/pytorch/extension-cpp",
        "https://github.example.com/owner/repo",
        "https://github.com:443/owner/repo",
        "https://github.com/owner/repo?tab=readme",
        "https://github.com/owner/repo#readme",
        "https://github.com/owner/repo/issues",
        "https://github.com/owner/repo name",
        "file:///tmp/repo",
        "C:\\repo",
        "https://127.0.0.1/repo",
    ],
)
def test_non_public_or_credentialed_urls_are_rejected(url: str) -> None:
    with pytest.raises(MxReadyError) as error:
        parse_repository_url(url)

    assert error.value.code in {
        "INVALID_REPOSITORY_URL",
        "UNSUPPORTED_REPOSITORY_HOST",
    }


@pytest.mark.parametrize(
    "value",
    [None, "main", "v1.2.0", "release/2026-07", "a" * 40],
)
def test_git_ref_accepts_bounded_branch_tag_and_commit_names(value: str | None) -> None:
    assert validate_git_ref(value) == value


@pytest.mark.parametrize(
    "value",
    [
        "",
        "--upload-pack=malicious",
        "feature/../secret",
        "feature@{1}",
        "feature\\windows",
        "feature/",
        "feature name",
        "main\nmalicious",
        "a" * 201,
    ],
)
def test_git_ref_rejects_unsafe_or_unbounded_values(value: str) -> None:
    with pytest.raises(MxReadyError) as error:
        validate_git_ref(value)

    assert error.value.code == "INVALID_GIT_REF"


def test_build_providers_keeps_default_short_names() -> None:
    assert build_providers(["github.com", "gitee.com"]) == {
        "github.com": "github",
        "gitee.com": "gitee",
    }


def test_build_providers_maps_custom_hosts_to_themselves() -> None:
    assert build_providers(["gitlab.example.com", "  ", ""]) == {
        "gitlab.example.com": "gitlab.example.com",
    }


def test_custom_provider_host_is_accepted_and_identified() -> None:
    providers = build_providers(["gitlab.example.com"])
    identity = parse_repository_url(
        "https://gitlab.example.com/acme/widgets",
        providers,
    )

    assert identity.provider == "gitlab.example.com"
    assert identity.owner == "acme"
    assert identity.name == "widgets"
    assert identity.clone_url == "https://gitlab.example.com/acme/widgets.git"


def test_default_hosts_stay_rejected_when_whitelist_is_custom() -> None:
    providers = build_providers(["gitlab.example.com"])

    with pytest.raises(MxReadyError) as error:
        parse_repository_url("https://github.com/owner/repo", providers)

    assert error.value.code == "UNSUPPORTED_REPOSITORY_HOST"


def test_parse_repository_url_without_providers_uses_builtin_whitelist() -> None:
    identity = parse_repository_url("https://gitee.com/metax-maca/cu-bridge")

    assert identity.provider == "gitee"
