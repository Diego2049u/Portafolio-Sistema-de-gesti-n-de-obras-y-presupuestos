import { useCallback, useEffect, useState } from 'react';
import { BrowserRouter, Link, Navigate, Route, Routes } from 'react-router-dom';
import Auth from './pages/Auth';
import loginBackground from './assets/background_logi.jpg';
import Dashboard from './pages/Dashboard';
import ObrasProyectos from './pages/ObrasProyectos';
import PresupuestosCostos from './pages/PresupuestosCostos';
import CostosMateriales from './pages/CostosMateriales';
import FacturacionCobranza from './pages/FacturacionCobranza';
import ClientesContratos from './pages/ClientesContratos';
import Auditoria from './pages/Auditoria';
import Tecnicos from './pages/Tecnicos';
import TecnicoDisponibilidad from './pages/TecnicoDisponibilidad';
import MainLayout from './components/layout';
import { api } from './api/client';
import { getDefaultPath, getRoleLabel, NAV_ITEMS, normalizeRole } from './config/navegacion';

const PAGE_BY_ID = {
  dashboard: Dashboard,
  obras: ObrasProyectos,
  presupuestos: PresupuestosCostos,
  costos: CostosMateriales,
  facturacion: FacturacionCobranza,
  clientes: ClientesContratos,
  auditoria: Auditoria,
  tecnicos: Tecnicos,
  'mi-horario': TecnicoDisponibilidad,
};

function createSessionUser(apiUser) {
  return {
    id: apiUser.id,
    name: apiUser.name,
    email: apiUser.email,
    role: normalizeRole(apiUser.role),
    roleLabel: getRoleLabel(apiUser.role),
    isAuthenticated: true,
  };
}

function RoutePage({ item, user, onLogout, page }) {
  const role = normalizeRole(user.role);
  const allowed = item.roles.some((allowedRole) => normalizeRole(allowedRole) === role);
  if (!allowed) return <Navigate to="/403" replace />;

  const Page = page || PAGE_BY_ID[item.id];
  if (!Page) return <Navigate to="/404" replace />;

  return (
    <MainLayout breadcrumb={item.label} period="Q4-2026" user={user} onLogout={onLogout}>
      <Page user={user} userRole={user.role} userName={user.name} />
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

function SessionLoading({ onRetry, error }) {
  return (
    <main className="min-h-screen flex items-center justify-center bg-surface-container-low p-6">
      <section className="max-w-md rounded-xl bg-surface-container-lowest p-8 text-center shadow-sm">
        <span className="material-symbols-outlined text-4xl text-primary">{error ? 'cloud_off' : 'progress_activity'}</span>
        <h1 className="mt-3 font-headline-md text-headline-md font-bold text-on-surface">
          {error ? 'No se pudo conectar con FYAG' : 'Verificando sesión…'}
        </h1>
        {error && <p className="mt-2 font-body-md text-body-md text-on-surface-variant">{error}</p>}
        {error && <button onClick={onRetry} className="mt-5 rounded-lg bg-primary-container px-4 py-2 font-label-md text-label-md font-semibold text-on-primary" type="button">Reintentar</button>}
      </section>
    </main>
  );
}

function AppRoutes() {
  const [session, setSession] = useState({ status: 'loading', user: null, error: '' });
  const [avisoSesion, setAvisoSesion] = useState('');

  const loadSession = useCallback(async () => {
    setSession({ status: 'loading', user: null, error: '' });
    try {
      const apiUser = await api.auth.me();
      setSession({ status: 'authenticated', user: createSessionUser(apiUser), error: '' });
    } catch (error) {
      if (error.status === 401) {
        setSession({ status: 'anonymous', user: null, error: '' });
      } else {
        setSession({ status: 'error', user: null, error: error.message || 'Verifica que el backend esté disponible.' });
      }
    }
  }, []);

  useEffect(() => {
    loadSession();
  }, [loadSession]);

  const handleLoginSuccess = useCallback((apiUser) => {
    setAvisoSesion('');
    setSession({ status: 'authenticated', user: createSessionUser(apiUser), error: '' });
  }, []);

  const handleLogout = useCallback(async () => {
    let aviso = '';
    try {
      await api.auth.logout();
    } catch {
      aviso = 'La sesión se cerró en esta ventana, pero el servidor no confirmó la revocación.';
    } finally {
      setAvisoSesion(aviso);
      setSession({ status: 'anonymous', user: null, error: '' });
    }
  }, []);

  if (session.status === 'loading' || session.status === 'error') {
    return <SessionLoading onRetry={loadSession} error={session.status === 'error' ? session.error : ''} />;
  }

  const user = session.user;
  const home = user ? getDefaultPath(user.role) : null;

  return (
    <Routes>
      <Route
        path="/login"
        element={user
          ? (home ? <Navigate to={home} replace /> : <AccessPage user={user} title="Sin páginas asignadas" detail="Tu rol no tiene módulos habilitados." />)
          : <div style={{ backgroundImage: `url(${loginBackground})` }} className="min-h-screen bg-surface bg-cover bg-center bg-no-repeat font-body-md text-body-md text-on-surface antialiased flex items-center justify-center p-4"><div className="w-full"><Auth onLoginSuccess={handleLoginSuccess} />{avisoSesion && <p role="status" className="mx-auto mt-3 max-w-md text-center text-body-sm text-error">{avisoSesion}</p>}</div></div>}
      />

      {NAV_ITEMS.map((item) => (
        <Route
          key={item.id}
          path={item.path}
          element={user ? <RoutePage item={item} user={user} onLogout={handleLogout} /> : <Navigate to="/login" replace />}
        />
      ))}

      <Route
        path="/tecnicos/:tecnicoId"
        element={user
          ? <RoutePage item={NAV_ITEMS.find((item) => item.id === 'tecnicos')} page={TecnicoDisponibilidad} user={user} onLogout={handleLogout} />
          : <Navigate to="/login" replace />}
      />

      <Route path="/403" element={user ? <AccessPage user={user} title="Acceso restringido" detail="Tu rol no tiene permiso para abrir este módulo." /> : <Navigate to="/login" replace />} />
      <Route path="/404" element={user ? <AccessPage user={user} title="Página no encontrada" detail="La dirección solicitada no corresponde a un módulo disponible." /> : <Navigate to="/login" replace />} />
      <Route path="/" element={user ? (home ? <Navigate to={home} replace /> : <AccessPage user={user} title="Sin páginas asignadas" detail="Tu rol no tiene módulos habilitados." />) : <Navigate to="/login" replace />} />
      <Route path="*" element={user ? (home ? <Navigate to={home} replace /> : <AccessPage user={user} title="Sin páginas asignadas" detail="Tu rol no tiene módulos habilitados." />) : <Navigate to="/login" replace />} />
    </Routes>
  );
}

export default function App() {
  return <BrowserRouter><AppRoutes /></BrowserRouter>;
}
