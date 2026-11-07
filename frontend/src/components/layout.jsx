import Sidebar from './Sidebar';
import Header from './Header';

export default function MainLayout({ children, breadcrumb, period, userRole = 'gerencia' }) {
  return (
    <div className="flex min-h-screen bg-surface-container-low text-on-surface font-sans">
      <Sidebar userRole={userRole} />
      <div className="flex-1 flex flex-col min-w-0">
        <Header breadcrumb={breadcrumb} period={period} />
        <main className="flex-1 p-6 md:p-8 overflow-y-auto">{children}</main>
      </div>
    </div>
  );
}
