"""Load and validate config.toml."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = ROOT / "config.toml"


@dataclass(frozen=True)
class Column:
    key: str
    name_en: str
    name_zh: str
    topics: tuple[str, ...]
    all_time: bool = False


@dataclass(frozen=True)
class Exclude:
    name_prefixes: tuple[str, ...]
    topics: frozenset[str]
    repos: frozenset[str]


@dataclass(frozen=True)
class Config:
    title: str
    base_url: str
    list_size: int
    min_stars_candidate: int
    min_stars_rising: int
    hot_days: int
    rising_days: int
    translation_model: str
    exclude: Exclude
    columns: tuple[Column, ...]


class ConfigError(ValueError):
    pass


def load_config(path: Path = DEFAULT_CONFIG) -> Config:
    with open(path, "rb") as f:
        raw = tomllib.load(f)
    try:
        site, ranking, translation = raw["site"], raw["ranking"], raw["translation"]
        exclude = raw.get("exclude", {})
        columns = tuple(
            Column(
                key=c["key"],
                name_en=c["name_en"],
                name_zh=c["name_zh"],
                topics=tuple(t.lower() for t in c["topics"]),
                all_time=bool(c.get("all_time", False)),
            )
            for c in raw["columns"]
        )
        config = Config(
            title=site["title"],
            base_url=site["base_url"],
            list_size=int(ranking["list_size"]),
            min_stars_candidate=int(ranking["min_stars_candidate"]),
            min_stars_rising=int(ranking["min_stars_rising"]),
            hot_days=int(ranking["hot_days"]),
            rising_days=int(ranking["rising_days"]),
            translation_model=translation["model"],
            exclude=Exclude(
                name_prefixes=tuple(p.lower() for p in exclude.get("name_prefixes", [])),
                topics=frozenset(t.lower() for t in exclude.get("topics", [])),
                repos=frozenset(r.lower() for r in exclude.get("repos", [])),
            ),
            columns=columns,
        )
    except KeyError as e:
        raise ConfigError(f"config.toml is missing required key: {e}") from e

    if not config.columns:
        raise ConfigError("config.toml must define at least one [[columns]]")
    keys = [c.key for c in config.columns]
    if len(set(keys)) != len(keys):
        raise ConfigError(f"duplicate column keys: {keys}")
    for c in config.columns:
        if not c.topics:
            raise ConfigError(f"column {c.key!r} has no topics")
    if config.rising_days >= config.hot_days:
        raise ConfigError("rising_days must be shorter than hot_days")
    return config
