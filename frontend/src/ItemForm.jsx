import { useState } from 'react';

const EMPTY = { name: '', sku: '', category: 'General', quantity: 0, reorder_level: 5, unit_price: 0, supplier: '' };
const NUMBERS = ['quantity', 'reorder_level', 'unit_price'];

export default function ItemForm({ item, onSave, onClose }) {
  const [form, setForm] = useState(item ? { ...EMPTY, ...item } : EMPTY);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  const set = (key) => (e) => setForm({ ...form, [key]: NUMBERS.includes(key) ? Number(e.target.value) : e.target.value });

  async function submit(e) {
    e.preventDefault();
    setSaving(true);
    setError('');
    try {
      const { name, sku, category, quantity, reorder_level, unit_price, supplier } = form;
      await onSave({ name, sku, category, quantity, reorder_level, unit_price, supplier });
    } catch (err) {
      setError(err.message);
      setSaving(false);
    }
  }

  return (
    <div className="overlay" onClick={onClose}>
      <form className="modal" onSubmit={submit} onClick={(e) => e.stopPropagation()}>
        <h2>{item ? 'Edit item' : 'New item'}</h2>
        <div className="grid">
          <label className="wide">Name<input required value={form.name} onChange={set('name')} /></label>
          <label>SKU<input required value={form.sku} onChange={set('sku')} /></label>
          <label>Category<input value={form.category} onChange={set('category')} /></label>
          <label>Quantity<input type="number" min="0" value={form.quantity} onChange={set('quantity')} /></label>
          <label>Reorder at<input type="number" min="0" value={form.reorder_level} onChange={set('reorder_level')} /></label>
          <label>Unit price<input type="number" min="0" step="0.01" value={form.unit_price} onChange={set('unit_price')} /></label>
          <label>Supplier<input value={form.supplier} onChange={set('supplier')} /></label>
        </div>
        {error && <p className="error">{error}</p>}
        <div className="actions">
          <button type="button" className="ghost" onClick={onClose}>Cancel</button>
          <button type="submit" disabled={saving}>{saving ? 'Saving...' : 'Save'}</button>
        </div>
      </form>
    </div>
  );
}
