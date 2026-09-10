"""Product/Service Catalog -- see app/models/catalog.py for field
rationale. Backs Sales Quotation lines (app/routers/quotations.py)."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.catalog import Product
from app.models.core import User
from app.models.groups import AccessLevel
from app.schemas.schemas import ProductCreate, ProductOut, ProductUpdate
from app.services import audit
from app.services.authority import require_module_access

router = APIRouter(prefix="/api/catalog", tags=["catalog"])
MODULE = "sales"


def _product_or_404(db: Session, product_id: uuid.UUID, company_id: uuid.UUID) -> Product:
    product = db.get(Product, product_id)
    if not product or product.company_id != company_id:
        raise HTTPException(status_code=404, detail="Catalog item not found")
    return product


@router.get("", response_model=list[ProductOut])
def list_products(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_module_access(MODULE, AccessLevel.VIEW)),
):
    query = db.query(Product).filter(Product.company_id == current_user.company_id)
    if not include_inactive:
        query = query.filter(Product.is_active)
    return query.order_by(Product.name).all()


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
        "sales_price_sgd", "cost_sgd", "unit_of_measure", "tax_code", "is_active",
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
