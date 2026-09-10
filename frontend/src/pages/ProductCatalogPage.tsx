import { useEffect, useState, type FormEvent } from 'react'
import { api, type Product, type ProductType } from '../lib/api'

const money = (n: number) => n.toFixed(2)

export default function ProductCatalogPage() {
  const [items, setItems] = useState<Product[]>([])
  const [showInactive, setShowInactive] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [productType, setProductType] = useState<ProductType>('service')
  const [name, setName] = useState('')
  const [internalReference, setInternalReference] = useState('')
  const [productCategory, setProductCategory] = useState('')
  const [salesPrice, setSalesPrice] = useState('')
  const [unitOfMeasure, setUnitOfMeasure] = useState('')

  function refresh() {
    api.listCatalog(showInactive).then(setItems).catch((e) => setError(e.message))
  }

  useEffect(refresh, [showInactive])

  async function onCreate(e: FormEvent) {
    e.preventDefault()
    setError(null)
    try {
      await api.createCatalogItem({
        product_type: productType,
        name,
        internal_reference: internalReference || undefined,
        product_category: productCategory || undefined,
        sales_price_sgd: salesPrice === '' ? 0 : parseFloat(salesPrice),
        unit_of_measure: unitOfMeasure || undefined,
      })
      setName('')
      setInternalReference('')
      setProductCategory('')
      setSalesPrice('')
      setUnitOfMeasure('')
      refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add catalog item')
    }
  }

  async function onToggleActive(item: Product) {
    setError(null)
    try {
      await api.updateCatalogItem(item.id, { is_active: !item.is_active })
      refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update item')
    }
  }

  return (
    <div>
      <h1>Product / Service Catalog</h1>
      <p className="muted">
        Sellable items a Sales Quotation line can be drawn from. Sales Price is net of GST; each
        item sells under the tax code shown (default SR, the company's standard 9% rate).
      </p>
      {error && <div className="error-banner">{error}</div>}

      <div className="card">
        <h2>Add catalog item</h2>
        <form onSubmit={onCreate}>
          <div className="form-row">
            <label>Type</label>
            <select value={productType} onChange={(e) => setProductType(e.target.value as ProductType)}>
              <option value="service">Service</option>
              <option value="product">Product</option>
            </select>
          </div>
          <div className="form-row">
            <label>Product name</label>
            <input value={name} onChange={(e) => setName(e.target.value)} required />
          </div>
          <div className="form-row">
            <label>Internal reference</label>
            <input value={internalReference} onChange={(e) => setInternalReference(e.target.value)} />
          </div>
          <div className="form-row">
            <label>Product category</label>
            <input value={productCategory} onChange={(e) => setProductCategory(e.target.value)} />
          </div>
          <div className="form-row">
            <label>Sales price (SGD, net of GST)</label>
            <input
              type="number"
              min="0"
              step="0.01"
              value={salesPrice}
              onChange={(e) => setSalesPrice(e.target.value)}
            />
          </div>
          <div className="form-row">
            <label>Unit of measure</label>
            <input
              value={unitOfMeasure}
              onChange={(e) => setUnitOfMeasure(e.target.value)}
              placeholder="e.g. Hours, Monthly, Yearly, Units"
            />
          </div>
          <button type="submit" disabled={!name}>
            Add item
          </button>
        </form>
      </div>

      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2>Catalog ({items.length})</h2>
          <label style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 13 }}>
            <input type="checkbox" checked={showInactive} onChange={(e) => setShowInactive(e.target.checked)} />
            Show inactive
          </label>
        </div>
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Type</th>
              <th>Reference</th>
              <th>Category</th>
              <th>Sales price</th>
              <th>Unit</th>
              <th>Tax</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {items.map((i) => (
              <tr key={i.id}>
                <td>{i.name}</td>
                <td className="muted">{i.product_type}</td>
                <td className="muted">{i.internal_reference ?? '-'}</td>
                <td className="muted">{i.product_category ?? '-'}</td>
                <td>{money(i.sales_price_sgd)}</td>
                <td className="muted">{i.unit_of_measure ?? '-'}</td>
                <td className="muted">{i.tax_code}</td>
                <td>
                  <span className={`badge ${i.is_active ? 'active' : 'draft'}`}>
                    {i.is_active ? 'Active' : 'Inactive'}
                  </span>
                </td>
                <td>
                  <button className="secondary" onClick={() => onToggleActive(i)}>
                    {i.is_active ? 'Deactivate' : 'Reactivate'}
                  </button>
                </td>
              </tr>
            ))}
            {items.length === 0 && (
              <tr>
                <td colSpan={9} className="muted">
                  No catalog items yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
