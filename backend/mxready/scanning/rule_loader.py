from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlsplit

import yaml
from pydantic import Field, ValidationError, field_validator, model_validator

from mxready.errors import MxReadyError
from mxready.models import Severity, SourceReference, StrictModel

_RULE_ID = re.compile(r"MXR-[A-Z]+-[0-9]{3}")
_CATEGORY = re.compile(r"[a-z][a-z0-9-]*")
_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
_FACT_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_]*")
_RULE_FILE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*\.ya?ml")
_REGEX_FLAGS = {
    "ASCII": re.ASCII,
    "DOTALL": re.DOTALL,
    "IGNORECASE": re.IGNORECASE,
    "MULTILINE": re.MULTILINE,
    "VERBOSE": re.VERBOSE,
}
_MAX_RULE_FILE_BYTES = 1_048_576


class RulePattern(StrictModel):
    type: Literal["regex", "dependency", "fact"]
    expression: str | None = None
    flags: list[str] = Field(default_factory=list)
    name: str | None = None
    equals: bool | str | None = None

    @field_validator("flags")
    @classmethod
    def flags_are_supported_and_unique(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)) or any(flag not in _REGEX_FLAGS for flag in value):
            raise ValueError("regex flags must be supported and unique")
        return value

    @model_validator(mode="after")
    def pattern_contract_matches_type(self) -> RulePattern:
        if self.type == "regex":
            if (
                not isinstance(self.expression, str)
                or not self.expression.strip()
                or len(self.expression) > 1_000
                or self.name is not None
                or self.equals is not None
            ):
                raise ValueError("invalid regex pattern contract")
            try:
                re.compile(self.expression, regex_flags(self.flags))
            except re.error as error:
                raise ValueError("invalid regex expression") from error
            return self

        if self.type == "dependency":
            if (
                not isinstance(self.name, str)
                or _NAME.fullmatch(self.name) is None
                or self.expression is not None
                or self.flags
                or self.equals is not None
            ):
                raise ValueError("invalid dependency pattern contract")
            return self

        if (
            not isinstance(self.name, str)
            or _FACT_NAME.fullmatch(self.name) is None
            or self.equals is None
            or self.expression is not None
            or self.flags
        ):
            raise ValueError("invalid fact pattern contract")
        return self


class RuleDefinition(StrictModel):
    id: str
    version: int = Field(ge=1)
    title: str
    category: str
    severity: Severity
    file_globs: list[str] = Field(min_length=1)
    patterns: list[RulePattern] = Field(min_length=1)
    message: str
    recommendation: str
    references: list[SourceReference] = Field(min_length=1)

    @field_validator("id")
    @classmethod
    def id_has_public_format(cls, value: str) -> str:
        if _RULE_ID.fullmatch(value) is None:
            raise ValueError("invalid rule id")
        return value

    @field_validator("category")
    @classmethod
    def category_has_stable_format(cls, value: str) -> str:
        if _CATEGORY.fullmatch(value) is None:
            raise ValueError("invalid rule category")
        return value

    @field_validator("title", "message", "recommendation")
    @classmethod
    def prose_is_non_empty(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("rule prose must not be empty")
        return stripped

    @field_validator("file_globs")
    @classmethod
    def file_globs_are_relative_and_unique(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("file globs must be unique")
        for pattern in value:
            if (
                not pattern
                or len(pattern) > 200
                or pattern.startswith(("/", "\\"))
                or "\\" in pattern
                or ".." in pattern.split("/")
            ):
                raise ValueError("file globs must be safe relative patterns")
        return value

    @field_validator("references")
    @classmethod
    def references_are_https(
        cls,
        value: list[SourceReference],
    ) -> list[SourceReference]:
        for reference in value:
            try:
                parsed = urlsplit(reference.url)
                port = parsed.port
            except ValueError as error:
                raise ValueError("invalid reference URL") from error
            if (
                not reference.title.strip()
                or not reference.url.startswith("https://")
                or parsed.scheme != "https"
                or not parsed.hostname
                or parsed.username is not None
                or parsed.password is not None
                or port is not None
            ):
                raise ValueError("rule references must use public HTTPS URLs")
        return value


class RuleCatalog(StrictModel):
    version: str
    rules: list[RuleDefinition]


class _RuleManifest(StrictModel):
    schema_version: Literal["1.0"]
    ruleset_version: str
    rule_files: list[str] = Field(min_length=1)

    @field_validator("ruleset_version")
    @classmethod
    def version_is_non_empty(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped or len(stripped) > 100:
            raise ValueError("invalid ruleset version")
        return stripped

    @field_validator("rule_files")
    @classmethod
    def files_are_safe_and_unique(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)) or any(
            _RULE_FILE.fullmatch(item) is None for item in value
        ):
            raise ValueError("invalid rule file list")
        return value


def load_rule_catalog(directory: Path) -> RuleCatalog:
    """Load a complete, strictly validated, versioned YAML rule catalog."""
    directory = Path(directory)
    try:
        manifest_document = _load_yaml(directory / "manifest.yml")
        manifest = _RuleManifest.model_validate(manifest_document)

        rules: list[RuleDefinition] = []
        seen_ids: set[str] = set()
        for filename in manifest.rule_files:
            document = _load_yaml(directory / filename)
            if not isinstance(document, list) or not document:
                raise _ruleset_invalid()
            for rule_document in document:
                rule = RuleDefinition.model_validate(rule_document)
                if rule.id in seen_ids:
                    raise _ruleset_invalid()
                seen_ids.add(rule.id)
                rules.append(rule)

        if not rules:
            raise _ruleset_invalid()
        return RuleCatalog(version=manifest.ruleset_version, rules=rules)
    except MxReadyError:
        raise
    except (
        OSError,
        TypeError,
        UnicodeError,
        ValidationError,
        ValueError,
        yaml.YAMLError,
    ) as error:
        raise _ruleset_invalid() from error


def regex_flags(flags: list[str]) -> re.RegexFlag:
    resolved = re.NOFLAG
    for flag in flags:
        resolved |= _REGEX_FLAGS[flag]
    return resolved


def _load_yaml(path: Path) -> Any:
    if path.stat().st_size > _MAX_RULE_FILE_BYTES:
        raise ValueError("rule file is too large")
    return yaml.safe_load(path.read_text(encoding="utf-8-sig"))


def _ruleset_invalid() -> MxReadyError:
    return MxReadyError(
        "RULESET_INVALID",
        "规则集无法加载或未通过校验，请检查规则文件。",
    )
