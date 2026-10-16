import { useCallback, useEffect, useState } from 'react';
import { api } from './api.js';
import ItemForm from './ItemForm.jsx';

const money = (n) => n.toLocaleString(undefined, { style: 'currency', currency: 'USD' });

function stockState(item) {
  if (item.quantity === 0) return ['out', 'Out of stock'];
  if (item.low_stock) return ['low', 'Low'];
  return ['ok', 'In stock'];
}

export default function App() {
  const [items, setItems] = useState([]);
  const [stats, setStats] = useState(null);
  const [search, setSearch] = useState('');
  const [lowOnly, setLowOnly] = useState(false);
  const [editing, setEditing] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    try {
      const params = {};
      if (search) params.q = search;
      if (lowOnly) params.low_stock = true;
      const [list, s] = await Promise.all([api.list(params), api.stats()]);
      setItems(list);
      setStats(s);
      setError('');
    } catch (err) {
      setError(`Can't reach the API: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }, [search, lowOnly]);

  useEffect(() => {
    const t = setTimeout(load, 200);
    return () => clearTimeout(t);
  }, [load]);

  async function run(action) {
    try {
      await action();
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  async function save(data) {
    if (editing.id) await api.update(editing.id, data);
    else await api.create(data);
    setEditing(null);
    await load();
  }

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="brand">▦ StockRoom</div>
        <nav>
          <a className={!lowOnly ? 'active' : ''} onClick={() => setLowOnly(false)}>All items</a>
          <a className={lowOnly ? 'active' : ''} onClick={() => setLowOnly(true)}>Needs reorder</a>
        </nav>
        <div className="sidebar-foot">v1.0 · FastAPI + Postgres</div>
      </aside>

      <main>
        <header>
          <div>
            <h1>Inventory</h1>
            <p className="muted">Track stock, spot low items, reorder before you run out.</p>
          </div>
          <button onClick={() => setEditing({})}>+ Add item</button>
        </header>

        {stats && (
          <section className="kpis">
            <div className="kpi"><span>Items</span><strong>{stats.total_items}</strong></div>
            <div className="kpi"><span>Units on hand</span><strong>{stats.total_units}</strong></div>
            <div className="kpi warn"><span>Low stock</span><strong>{stats.low_stock}</strong></div>
            <div className="kpi bad"><span>Out of stock</span><strong>{stats.out_of_stock}</strong></div>
            <div className="kpi"><span>Stock value</span><strong>{money(stats.inventory_value)}</strong></div>
          </section>
        )}

        <div className="toolbar">
          <input placeholder="Search by name or SKU" value={search} onChange={(e) => setSearch(e.target.value)} />
          <label className="check">
            <input type="checkbox" checked={lowOnly} onChange={(e) => setLowOnly(e.target.checked)} /> Low stock only
          </label>
        </div>

        {error && <div className="banner">{error}</div>}

        <div className="table-wrap">
          <table>
            <thead>
              <tr><th>Item</th><th>Category</th><th>Stock</th><th>Price</th><th>Status</th><th /></tr>
            </thead>
            <tbody>
              {loading && <tr><td colSpan="6" className="empty">Loading...</td></tr>}
              {!loading && items.length === 0 && <tr><td colSpan="6" className="empty">Nothing here yet.</td></tr>}
              {items.map((item) => {
                const [cls, label] = stockState(item);
                return (
                  <tr key={item.id}>
                    <td data-label="Item">
                      <div className="name">{item.name}</div>
                      <div className="muted small">{item.sku}{item.supplier && ` · ${item.supplier}`}</div>
                    </td>
                    <td data-label="Category">{item.category}</td>
                    <td data-label="Stock">
                      <div className="stepper">
                        <button className="ghost" disabled={item.quantity === 0} onClick={() => run(() => api.adjust(item.id, -1))}>−</button>
                        <span>{item.quantity}</span>
                        <button className="ghost" onClick={() => run(() => api.adjust(item.id, 1))}>+</button>
                      </div>
                      <div className="muted small">reorder at {item.reorder_level}</div>
                    </td>
                    <td data-label="Price">{money(item.unit_price)}</td>
                    <td data-label="Status"><span className={`badge ${cls}`}>{label}</span></td>
                    <td className="row-actions">
                      <button className="ghost" onClick={() => setEditing(item)}>Edit</button>
                      <button className="ghost danger" onClick={() => run(() => api.remove(item.id))}>Delete</button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </main>

      {editing && <ItemForm item={editing.id ? editing : null} onSave={save} onClose={() => setEditing(null)} />}
    </div>
  );
}
