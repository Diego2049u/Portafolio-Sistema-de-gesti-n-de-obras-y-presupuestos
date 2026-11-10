// src/App.jsx
import { useState } from 'react';
import Auth from './pages/Auth';
import Dashboard from './pages/Dashboard';
import ObrasProyectos from './pages/ObrasProyectos';
import PresupuestosCostos from './pages/PresupuestosCostos';
import CostosMateriales from './pages/CostosMateriales';
import FacturacionCobranza from './pages/FacturacionCobranza';
import ClientesContratos from './pages/ClientesContratos';
import Auditoria from './pages/Auditoria';
import Layout from './components/layout';
import { ROLES } from './config/navegacion';

export default function App() {
  // Estado simulado de autenticación y rol (cambiar para probar diferentes roles)
  const [user, setUser] = useState({
    isAuthenticated: true, // Cambiar a false para probar Auth.jsx
    role: ROLES.ADMIN,     // Opciones: ADMIN, FINANZAS, SUPERVISOR, TECNICO
    name: 'Carlos Araya'
  });

  const [activeTab, setActiveTab] = useState('obras'); 

  if (!user.isAuthenticated) {
    return (
      <div className="bg-surface font-body-md text-body-md text-on-surface antialiased min-h-screen flex items-center justify-center p-4">
        <Auth onLoginSuccess={(userRole) => setUser({ isAuthenticated: true, role: userRole, name: 'Usuario Demo' })} />
      </div>
    );
  }

  // Mapeo dinámico de vistas
  const renderView = () => {
    switch (activeTab) {
      case 'dashboard':
        return <Dashboard userRole={user.role} />;
      case 'obras':
        return <ObrasProyectos userRole={user.role} userName={user.name} />;
      case 'presupuestos':
        return <PresupuestosCostos userRole={user.role} />;
      case 'costos':
        return <CostosMateriales userRole={user.role} />;
      case 'facturacion':
        return <FacturacionCobranza userRole={user.role} />;
      case 'clientes':
        return <ClientesContratos userRole={user.role} />;
      case 'auditoria':
        return <Auditoria userRole={user.role} />;
      default:
        return <Dashboard userRole={user.role} />;
    }
  };

  return (
    <Layout 
      currentTab={activeTab} 
      onSelectTab={setActiveTab} 
      user={user}
      onLogout={() => setUser({ isAuthenticated: false, role: null, name: '' })}
    >
      {renderView()}
    </Layout>
  );
}
