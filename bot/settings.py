from __future__ import annotations

from dataclasses import dataclass, field
from typing import set as set_type


@dataclass
class Limits:
    max_recipe_title: int = 255
    max_recipe_body: int = 5000
    max_meal_text: int = 2000
    max_photo_size_bytes: int = 5 * 1024 * 1024
    allowed_photo_mime: set_type[str] = field(
        default_factory=lambda: {"image/jpeg", "image/png", "image/webp"}
    )


@dataclass
class AppSettings:
    limits: Limits = field(default_factory=Limits)


settings = AppSettings()
