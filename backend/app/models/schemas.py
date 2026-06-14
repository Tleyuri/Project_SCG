from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class LegendBBox(BaseModel):
    xmin: float
    ymin: float
    xmax: float
    ymax: float

    def as_tuple(self) -> tuple[float, float, float, float]:
        return (self.xmin, self.ymin, self.xmax, self.ymax)


class ExtractRequest(BaseModel):
    legend_bbox: Optional[LegendBBox] = None
    settings: Optional[dict] = None
    pipe_sizes: Optional[dict] = None
    layer_mapping: Optional[dict] = None
    price_table: Optional[dict] = None


class ExportRequest(ExtractRequest):
    garden_location: str = ""
    garden_phone: str = ""


class LayerMappingUpdate(BaseModel):
    mapping: dict


class PriceTableUpdate(BaseModel):
    price_table: dict


class PipeSizesUpdate(BaseModel):
    pipe_sizes: dict


class SettingsUpdate(BaseModel):
    settings: dict
