"""Product/Service Catalog -- see app/models/catalog.py for field
rationale. Backs Sales Quotation lines (app/routers/quotations.py)."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.catalog import Product
from app.models.core import User
from app.models.groups import AccessLevel
from app.schemas.schemas import ProductCreate, ProductOut, ProductUpdate
from app.services import audit, exports
from app.services.authority import require_module_access

router = APIRouter(prefix="/api/catalog", tags=["catalog"])
MODULE = "sales"

PRODUCT_EXPORT_FIELDS = [
    "name", "product_type", "internal_reference", "product_category", "tags",
    "sales_price_sgd", "cost_sgd", "unit_of_measure", "tax_code", "is_active",
]


def _product_or_404(db: Session, product_id: uuid.UUID, company_id: uuid.UUID) -> Product:
    product = db.get(Product, product_id)
    if not product or product.company_id != company_id:
        raise HTTPException(status_code=404, detail="Catalog item not found")
    return product


def _filter_products(db: Session, company_id: uuid.UUID, include_inactive: bool) -> list[Product]:
    query = db.query(Product).filter(Product.company_id == company_id)
    if not include_inactive:
        query = query.filter(Product.is_active)
    return query.order_by(Product.name).all()


@router.get("", response_model=list[ProductOut])
def list_products(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    return _filter_products(db, current_user.company_id, include_inactive)


def _product_row(p: Product) -> dict:
    return {
        "name": p.name,
        "product_type": p.product_type.value,
        "internal_reference": p.internal_reference or "",
        "product_category": p.product_category or "",
        "tags": p.tags or "",
        "sales_price_sgd": f"{float(p.sales_price_sgd):.2f}",
        "cost_sgd": f"{float(p.cost_sgd):.2f}" if p.cost_sgd is not None else "",
        "unit_of_measure": p.unit_of_measure or "",
        "tax_code": p.tax_code,
        "is_active": p.is_active,
    }


@router.get("/export.csv")
def export_products_csv(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    rows = [_product_row(p) for p in _filter_products(db, current_user.company_id, include_inactive)]
    csv_text = exports.rows_to_csv(PRODUCT_EXPORT_FIELDS, rows)
    return StreamingResponse(
        iter([csv_text]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=product-catalog.csv"},
    )


@router.get("/export.xlsx")
def export_products_excel(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    rows = [_product_row(p) for p in _filter_products(db, current_user.company_id, include_inactive)]
    data = exports.rows_to_excel(PRODUCT_EXPORT_FIELDS, rows, sheet_name="Product Catalog")
    return StreamingResponse(
        iter([data]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=product-catalog.xlsx"},
    )


@router.post("", response_model=ProductOut)
def create_product(
    payload: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    product = Product(company_id=current_user.company_id, **payload.model_dump())
    db.add(product)
    db.flush()
    audit.record(
        db,
        entity_type="product",
        entity_id=product.id,
        action="created",
        actor_user_id=current_user.id,
        details=f"name={payload.name}",
        new_value={"name": payload.name, "sales_price_sgd": payload.sales_price_sgd},
    )
    db.commit()
    db.refresh(product)
    return product


@router.patch("/{product_id}", response_model=ProductOut)
def update_product(
    product_id: uuid.UUID,
    payload: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.EDIT)),
):
    product = _product_or_404(db, product_id, current_user.company_id)
    fields = payload.model_dump(exclude_unset=True)
    old_value: dict[str, object] = {}
    new_value: dict[str, object] = {}
    for field in (
        "product_type", "name", "internal_reference", "product_category", "tags",
        "sales_price_sgd", "cost_sgd", "unit_of_measure", "tax_code",
        "default_reference_code_id", "is_active",
    ):
        if field not in fields:
            continue
        old = getattr(product, field)
        new = fields[field]
        if old == new:
            continue
        old_value[field] = old.value if hasattr(old, "value") else old
        new_value[field] = new.value if hasattr(new, "value") else new
        setattr(product, field, new)

    audit.record(
        db,
        entity_type="product",
        entity_id=product.id,
        action="updated",
        actor_user_id=current_user.id,
        old_value=old_value or None,
        new_value=new_value or None,
    )
    db.commit()
    db.refresh(product)
    return product
