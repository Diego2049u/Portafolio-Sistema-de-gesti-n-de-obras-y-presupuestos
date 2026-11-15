import { useState } from 'react';
import { BrowserRouter, Link, Navigate, Route, Routes } from 'react-router-dom';
import Auth from './pages/Auth';
import Dashboard from './pages/Dashboard';
import ObrasProyectos from './pages/ObrasProyectos';
import PresupuestosCostos from './pages/PresupuestosCostos';
import CostosMateriales from './pages/CostosMateriales';
import FacturacionCobranza from './pages/FacturacionCobranza';
import ClientesContratos from './pages/ClientesContratos';
import Auditoria from './pages/Auditoria';
import Tecnicos from './pages/Tecnicos';
import MainLayout from './components/layout';
import { getDefaultPath, getRoleLabel, NAV_ITEMS, normalizeRole, ROLES } from './config/navegacion';

const PAGE_BY_ID = {
  dashboard: Dashboard,
  obras: ObrasProyectos,
  presupuestos: PresupuestosCostos,
  costos: CostosMateriales,
  facturacion: FacturacionCobranza,
  clientes: ClientesContratos,
  auditoria: Auditoria,
  tecnicos: Tecnicos,
};

function RoutePage({ item, user }) {
  if (!user.isAuthenticated) return <Navigate to="/login" replace />;

  const role = normalizeRole(user.role);
  const allowed = item.roles.some((allowedRole) => normalizeRole(allowedRole) === role);
  if (!allowed) return <Navigate to="/403" replace />;

  const Page = PAGE_BY_ID[item.id];
  if (!Page) return <Navigate to="/404" replace />;

  return (
    <MainLayout breadcrumb={item.label} period="Q4-2026" user={user}>
      <Page userRole={user.role} userName={user.name} />
    </MainLayout>
  );
}

function AccessPage({ user, title, detail }) {
  const home = getDefaultPath(user.role);
  return (
    <div className="min-h-screen flex items-center justify-center bg-surface-container-low p-6">
      <section className="max-w-lg rounded-xl bg-surface-container-lowest p-8 text-center shadow-sm">
        <span className="material-symbols-outlined text-4xl text-secondary">lock</span>
        <h1 className="mt-3 font-headline-md text-headline-md font-bold text-on-surface">{title}</h1>
        <p className="mt-2 font-body-md text-body-md text-on-surface-variant">{detail}</p>
        {home && <Link className="mt-5 inline-flex rounded-lg bg-primary-container px-4 py-2 font-label-md text-label-md font-semibold text-on-primary" to={home}>Ir a mi inicio</Link>}
      </section>
    </div>
  );
}

function AppRoutes() {
  // Sesión de demostración temporal; el inicio de sesión real se conectará al backend en la integración.
  const [user, setUser] = useState({
    isAuthenticated: true,
    role: ROLES.GERENCIA,
    name: 'Carlos Araya',
    roleLabel: getRoleLabel(ROLES.GERENCIA),
  });
  const home = getDefaultPath(user.role);

  return (
    <Routes>
      <Route
        path="/login"
        element={user.isAuthenticated
          ? (home ? <Navigate to={home} replace /> : <AccessPage user={user} title="Sin páginas asignadas" detail="Tu rol no tiene módulos habilitados." />)
          : <div className="min-h-screen bg-surface font-body-md text-body-md text-on-surface antialiased flex items-center justify-center p-4"><Auth onLoginSuccess={(role) => setUser({ isAuthenticated: true, role, name: 'Usuario Demo', roleLabel: getRoleLabel(role) })} /></div>}
      />

      {NAV_ITEMS.map((item) => (
        <Route key={item.id} path={item.path} element={<RoutePage item={item} user={user} />} />
      ))}

      <Route
        path="/403"
        element={user.isAuthenticated
          ? <AccessPage user={user} title="Acceso restringido" detail="Tu rol no tiene permiso para abrir este módulo." />
          : <Navigate to="/login" replace />}
      />
      <Route
        path="/404"
        element={user.isAuthenticated
          ? <AccessPage user={user} title="Página no encontrada" detail="La dirección solicitada no corresponde a un módulo disponible." />
          : <Navigate to="/login" replace />}
      />
      <Route
        path="/"
        element={user.isAuthenticated
          ? (home ? <Navigate to={home} replace /> : <AccessPage user={user} title="Sin páginas asignadas" detail="Tu rol no tiene módulos habilitados." />)
          : <Navigate to="/login" replace />}
      />
      <Route
        path="*"
        element={user.isAuthenticated
          ? (home ? <Navigate to={home} replace /> : <AccessPage user={user} title="Sin páginas asignadas" detail="Tu rol no tiene módulos habilitados." />)
          : <Navigate to="/login" replace />}
      />
    </Routes>
  );
}

export default function App() {
  return <BrowserRouter><AppRoutes /></BrowserRouter>;
}
