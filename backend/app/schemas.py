from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field


class ItemBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    sku: str = Field(min_length=1, max_length=64)
    category: str = Field(default="General", max_length=80)
    quantity: int = Field(default=0, ge=0)
    reorder_level: int = Field(default=5, ge=0)
    unit_price: float = Field(default=0.0, ge=0)
    supplier: str = Field(default="", max_length=120)


class ItemCreate(ItemBase):
    pass


class ItemUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    sku: str | None = Field(default=None, min_length=1, max_length=64)
    category: str | None = Field(default=None, max_length=80)
    quantity: int | None = Field(default=None, ge=0)
    reorder_level: int | None = Field(default=None, ge=0)
    unit_price: float | None = Field(default=None, ge=0)
    supplier: str | None = Field(default=None, max_length=120)


class ItemOut(ItemBase):
    id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def low_stock(self) -> bool:
        return self.quantity <= self.reorder_level


class StockAdjust(BaseModel):
    delta: int = Field(description="Positive to receive stock, negative to ship it")
    reason: str = Field(default="", max_length=200)


class StatsOut(BaseModel):
    total_items: int
    total_units: int
    low_stock: int
    out_of_stock: int
    inventory_value: float
    categories: dict[str, int]
