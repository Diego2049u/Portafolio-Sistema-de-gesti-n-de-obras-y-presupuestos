import { createContext, useContext } from 'react';
import Sidebar from './Sidebar';
import Header from './Header';

const LayoutContext = createContext(false);

export default function MainLayout({
  children,
  breadcrumb,
  period,
  userRole,
  user,
  currentTab,
  onSelectTab
}) {
  const isNestedLayout = useContext(LayoutContext);

  // Las páginas históricamente incluyen MainLayout. Cuando App ya monta el
  // layout global, las instancias internas deben aportar solo su contenido.
  if (isNestedLayout) return children;

  return (
    <LayoutContext.Provider value>
      <div className="flex min-h-screen bg-surface-container-low text-on-surface font-sans">
        <Sidebar
          userRole={userRole || user?.role}
          currentTab={currentTab}
          onSelectTab={onSelectTab}
        />
        <div className="flex-1 flex flex-col min-w-0">
          <Header breadcrumb={breadcrumb} period={period} />
          <main className="flex-1 p-6 md:p-8 overflow-y-auto">{children}</main>
        </div>
      </div>
    </LayoutContext.Provider>
  );
}
