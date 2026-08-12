from __future__ import annotations

from uuid import UUID

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from .common import OrmModel


class TailorServiceIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, populate_by_name=True)

    service_name: str = Field(validation_alias=AliasChoices("service_name", "serviceName"), min_length=2, max_length=160)
    category: str = Field(default="Other", max_length=80)
    price: int = Field(gt=0)
    description: str | None = None
    is_combo: bool = Field(default=False, validation_alias=AliasChoices("is_combo", "isCombo"))
    combo_items: list[str] | None = Field(default=None, validation_alias=AliasChoices("combo_items", "comboItems"))


class TailorServicePatchIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, populate_by_name=True)

    service_name: str | None = Field(default=None, validation_alias=AliasChoices("service_name", "serviceName"), min_length=2, max_length=160)
    category: str | None = Field(default=None, max_length=80)
    price: int | None = Field(default=None, gt=0)
    description: str | None = None
    is_combo: bool | None = Field(default=None, validation_alias=AliasChoices("is_combo", "isCombo"))
    combo_items: list[str] | None = Field(default=None, validation_alias=AliasChoices("combo_items", "comboItems"))
    is_active: bool | None = Field(default=None, validation_alias=AliasChoices("is_active", "isActive"))


class TailorServiceOut(OrmModel):
    service_id: UUID
    tailor_id: UUID | str
    id: str | None = None
    serviceId: str | None = None
    serviceUuid: str | None = None
    service_name: str | None = None
    serviceName: str | None = None
    name: str | None = None
    category: str | None = None
    price: int
    is_combo: bool = False
    isCombo: bool = False
    combo_items: list[str] = Field(default_factory=list)
    comboItems: list[str] = Field(default_factory=list)
    description: str | None = None
    is_active: bool = True
    isActive: bool = True
