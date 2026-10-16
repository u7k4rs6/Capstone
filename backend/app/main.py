from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from prometheus_client import Counter
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .config import settings
from .db import Base, engine, get_db
from .models import Item
from .schemas import ItemCreate, ItemOut, ItemUpdate, StatsOut, StockAdjust

STOCK_MOVEMENTS = Counter(
    "stockroom_stock_movements_total",
    "Units moved through stock adjustments",
    ["direction"],
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Containers run Alembic before Uvicorn. create_all is a no-op there and keeps tests self-contained.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)
Instrumentator(excluded_handlers=["/metrics", "/health", "/ready"]).instrument(app).expose(app, endpoint="/metrics")


def get_item_or_404(item_id: int, db: Session) -> Item:
    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


def commit_or_409(db: Session):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="SKU already exists")


@app.get("/")
def root():
    return {"service": settings.app_name, "version": settings.app_version, "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "UP"}


@app.get("/ready")
def ready(db: Session = Depends(get_db)):
    db.execute(select(func.count(Item.id)))
    return {"status": "READY"}


@app.get("/api/items", response_model=list[ItemOut])
def list_items(
    q: str | None = None,
    category: str | None = None,
    low_stock: bool = False,
    db: Session = Depends(get_db),
):
    query = select(Item).order_by(Item.name)
    if q:
        like = f"%{q}%"
        query = query.where(or_(Item.name.ilike(like), Item.sku.ilike(like)))
    if category:
        query = query.where(Item.category == category)
    if low_stock:
        query = query.where(Item.quantity <= Item.reorder_level)
    return list(db.scalars(query))


@app.get("/api/stats", response_model=StatsOut)
def stats(db: Session = Depends(get_db)):
    items = list(db.scalars(select(Item)))
    categories: dict[str, int] = {}
    for item in items:
        categories[item.category] = categories.get(item.category, 0) + 1
    return StatsOut(
        total_items=len(items),
        total_units=sum(i.quantity for i in items),
        low_stock=sum(1 for i in items if i.quantity <= i.reorder_level),
        out_of_stock=sum(1 for i in items if i.quantity == 0),
        inventory_value=round(sum(i.quantity * i.unit_price for i in items), 2),
        categories=categories,
    )


@app.get("/api/items/{item_id}", response_model=ItemOut)
def get_item(item_id: int, db: Session = Depends(get_db)):
    return get_item_or_404(item_id, db)


@app.post("/api/items", response_model=ItemOut, status_code=status.HTTP_201_CREATED)
def create_item(payload: ItemCreate, db: Session = Depends(get_db)):
    item = Item(**payload.model_dump())
    db.add(item)
    commit_or_409(db)
    db.refresh(item)
    return item


@app.put("/api/items/{item_id}", response_model=ItemOut)
def update_item(item_id: int, payload: ItemUpdate, db: Session = Depends(get_db)):
    item = get_item_or_404(item_id, db)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    commit_or_409(db)
    db.refresh(item)
    return item


@app.post("/api/items/{item_id}/adjust", response_model=ItemOut)
def adjust_stock(item_id: int, payload: StockAdjust, db: Session = Depends(get_db)):
    item = get_item_or_404(item_id, db)
    if item.quantity + payload.delta < 0:
        raise HTTPException(status_code=400, detail=f"Only {item.quantity} units in stock")
    item.quantity += payload.delta
    db.commit()
    db.refresh(item)
    STOCK_MOVEMENTS.labels(direction="in" if payload.delta > 0 else "out").inc(abs(payload.delta))
    return item


@app.delete("/api/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(item_id: int, db: Session = Depends(get_db)):
    item = get_item_or_404(item_id, db)
    db.delete(item)
    db.commit()
