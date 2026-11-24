import { useMemo, useState } from 'react';

const collator = new Intl.Collator('es-CL', { numeric: true, sensitivity: 'base' });

export function useTablePagination(rows, { pageSize = 25, filterKey } = {}) {
  const [position, setPosition] = useState({ page: 1, filterKey });
  const [sort, setSort] = useState(null);
  const ordered = useMemo(() => {
    if (!sort) return rows;
    return [...rows].sort((left, right) => {
      const a = sort.value(left);
      const b = sort.value(right);
      if (a == null || a === '') return b == null || b === '' ? 0 : 1;
      if (b == null || b === '') return -1;
      const comparison = typeof a === 'number' && typeof b === 'number'
        ? a - b : collator.compare(a, b);
      return sort.direction === 'ascending' ? comparison : -comparison;
    });
  }, [rows, sort]);
  const pageCount = Math.max(1, Math.ceil(rows.length / pageSize));
  const page = position.filterKey === filterKey ? Math.min(position.page, pageCount) : 1;
  const start = (page - 1) * pageSize;

  function setPage(nextPage) {
    setPosition({ page: nextPage, filterKey });
  }

  function sortBy(label, value) {
    setSort((current) => ({
      label,
      value,
      direction: current?.label === label && current.direction === 'ascending' ? 'descending' : 'ascending',
    }));
    setPage(1);
  }

  return { rows: ordered.slice(start, start + pageSize), page, pageCount, setPage, sort, sortBy };
}
