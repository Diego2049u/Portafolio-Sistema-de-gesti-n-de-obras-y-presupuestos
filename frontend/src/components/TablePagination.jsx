export function SortableHeader({ label, value, table }) {
  if (!value) return <th scope="col" className="p-3">{label}</th>;
  const direction = table.sort?.label === label ? table.sort.direction : undefined;
  return (
    <th scope="col" className="p-3" aria-sort={direction}>
      <button type="button" className="text-left uppercase hover:underline" onClick={() => table.sortBy(label, value)}>
        {label}{direction && <span aria-hidden="true"> {direction === 'ascending' ? '↑' : '↓'}</span>}
      </button>
    </th>
  );
}

export default function TablePagination({ table, label = 'Paginación' }) {
  const { page, pageCount, setPage } = table;
  if (pageCount === 1) return null;
  const button = 'rounded-lg border border-outline-variant px-3 py-2 text-sm disabled:opacity-50';
  return (
    <nav aria-label={label} className="flex flex-wrap items-center justify-end gap-2 pt-4">
      <button type="button" className={button} disabled={page === 1} onClick={() => setPage(page - 1)}>Anterior</button>
      <span className="px-1 text-sm text-secondary" aria-live="polite">Página {page} de {pageCount}</span>
      <button type="button" className={button} disabled={page === pageCount} onClick={() => setPage(page + 1)}>Siguiente</button>
    </nav>
  );
}
