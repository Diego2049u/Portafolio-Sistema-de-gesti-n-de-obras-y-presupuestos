import { useState } from 'react';
import flyagLogo from '../assets/flyag-logo-pag.png';

export default function Auth() {
  const [activeTab, setActiveTab] = useState('login');
  
  // Estados para la visibilidad de contraseñas
  const [showLoginPassword, setShowLoginPassword] = useState(false);
  const [showRegPassword, setShowRegPassword] = useState(false);
  const [showRegConfirmPassword, setShowRegConfirmPassword] = useState(false);

  // Estados de formularios
  const [loginData, setLoginData] = useState({
    email: 'c.araya@fyag.cl',
    password: '',
    remember: true,
  });

  const [registerData, setRegisterData] = useState({
    fullName: '',
    email: '',
    password: '',
    confirmPassword: '',
    role: 'operaciones',
  });

  const handleLoginSubmit = (e) => {
    e.preventDefault();
    console.log('Iniciar sesión:', loginData);
    // Aquí conectarás con la API de Django REST Framework
  };

  const handleRegisterSubmit = (e) => {
    e.preventDefault();
    console.log('Solicitar registro:', registerData);
    // Aquí conectarás con la API de Django REST Framework
  };

  return (
    <main className="w-full max-w-md mx-auto">
      <div className="flex flex-col w-full">
        <div className="relative w-full overflow-hidden bg-surface-container-lowest rounded-xl shadow-xl">
          {/* Ambient Structural Pattern */}
          <div className="absolute -top-24 -right-24 w-96 h-96 bg-primary/5 rounded-full blur-3xl pointer-events-none" />
          <div className="absolute -bottom-24 -left-24 w-80 h-80 bg-tertiary/5 rounded-full blur-2xl pointer-events-none" />

          <div className="relative z-10 p-6 md:p-8 flex flex-col gap-6">
            {/* Header Institucional */}
            <header className="flex flex-col gap-4">
              <div className="flex justify-center">
                <img
                  alt="Logo FLYAG"
                  className="h-16 w-auto max-w-full object-contain"
                  src={flyagLogo}
                />
              </div>

              <div className="bg-surface-container-low p-3.5 rounded-lg flex items-center gap-3">
                <div className="p-2 bg-primary/10 text-primary rounded-md shrink-0">
                  <span
                    className="material-symbols-outlined text-[20px]"
                    style={{ fontVariationSettings: "'FILL' 1" }}
                  >
                    assured_workload
                  </span>
                </div>
                <div className="flex flex-col min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-headline-sm text-headline-sm text-on-surface truncate">
                      ERP Obras & Presupuestos
                    </span>
                    <span className="bg-primary/10 text-primary font-label-sm text-[10px] px-1.5 py-0.5 rounded uppercase">
                      RBAC Active
                    </span>
                  </div>
                  <p className="font-body-sm text-body-sm text-secondary truncate">
                    Trazabilidad operativa, presupuestaria y logística FYAG
                  </p>
                </div>
              </div>
            </header>

            {/* Pestañas de navegación */}
            <div className="grid grid-cols-2 p-1 bg-surface-container rounded-lg">
              <button
                type="button"
                onClick={() => setActiveTab('login')}
                className={`py-2 text-center font-label-md text-label-md rounded-md transition-all duration-150 ${
                  activeTab === 'login'
                    ? 'bg-surface-container-lowest text-primary shadow-sm'
                    : 'text-secondary hover:text-on-surface'
                }`}
              >
                Iniciar Sesión
              </button>
              <button
                type="button"
                onClick={() => setActiveTab('register')}
                className={`py-2 text-center font-label-md text-label-md rounded-md transition-all duration-150 ${
                  activeTab === 'register'
                    ? 'bg-surface-container-lowest text-primary shadow-sm'
                    : 'text-secondary hover:text-on-surface'
                }`}
              >
                Solicitar Registro
              </button>
            </div>

            {/* FORMULARIO 1: INICIAR SESIÓN */}
            {activeTab === 'login' && (
              <form onSubmit={handleLoginSubmit} className="flex flex-col gap-4.5">
                <div className="flex flex-col gap-1.5">
                  <label htmlFor="login-identifier" className="font-label-sm text-label-sm text-on-surface-variant flex items-center justify-between">
                    <span>CORREO INSTITUCIONAL</span>
                  </label>
                  <div className="relative flex items-center">
                    <span className="material-symbols-outlined absolute left-3 text-secondary text-[18px]">
                      badge
                    </span>
                    <input
                      id="login-identifier"
                      type="email"
                      required
                      placeholder="ej. usuario@fyag.cl"
                      value={loginData.email}
                      onChange={(e) => setLoginData({ ...loginData, email: e.target.value })}
                      className="w-full bg-surface-container-low focus:bg-surface-container-lowest text-on-surface font-body-md text-body-md pl-10 pr-3 py-2 rounded-lg focus:outline-none transition-colors"
                    />
                  </div>
                </div>

                <div className="flex flex-col gap-1.5">
                  <div className="flex items-center justify-between">
                    <label htmlFor="login-password" className="font-label-sm text-label-sm text-on-surface-variant">
                      CONTRASEÑA DE ACCESO
                    </label>
                    <a href="#forgot" className="font-label-sm text-[11px] text-primary hover:underline">
                      ¿Olvidó contraseña?
                    </a>
                  </div>
                  <div className="relative flex items-center">
                    <span className="material-symbols-outlined absolute left-3 text-secondary text-[18px]">
                      key
                    </span>
                    <input
                      id="login-password"
                      type={showLoginPassword ? 'text' : 'password'}
                      required
                      placeholder="••••••••••••"
                      value={loginData.password}
                      onChange={(e) => setLoginData({ ...loginData, password: e.target.value })}
                      className="w-full bg-surface-container-low focus:bg-surface-container-lowest text-on-surface font-body-md text-body-md pl-10 pr-10 py-2 rounded-lg focus:outline-none transition-colors"
                    />
                    <button
                      type="button"
                      onClick={() => setShowLoginPassword(!showLoginPassword)}
                      className="absolute right-2 p-1 text-secondary hover:text-on-surface"
                      title="Alternar visibilidad"
                    >
                      <span className="material-symbols-outlined text-[18px]">
                        {showLoginPassword ? 'visibility_off' : 'visibility'}
                      </span>
                    </button>
                  </div>
                </div>

                <div className="flex items-center justify-between pt-1">
                  <label className="flex items-center gap-2 cursor-pointer select-none">
                    <input
                      type="checkbox"
                      checked={loginData.remember}
                      onChange={(e) => setLoginData({ ...loginData, remember: e.target.checked })}
                      className="w-4 h-4 rounded text-primary focus:ring-0 cursor-pointer"
                    />
                    <span className="font-body-sm text-body-sm text-secondary">
                      Recordar en esta estación
                    </span>
                  </label>
                </div>

                <button
                  type="submit"
                  className="w-full mt-2 bg-primary-container hover:bg-primary text-on-primary font-headline-sm text-headline-sm py-2.5 rounded-lg shadow-md hover:shadow-lg transition-all flex items-center justify-center gap-2 group"
                >
                  <span
                    className="material-symbols-outlined text-[20px] transition-transform group-hover:scale-110"
                    style={{ fontVariationSettings: "'FILL' 1" }}
                  >
                    lock_open
                  </span>
                  <span>Ingresar al ERP FYAG</span>
                </button>
              </form>
            )}

            {/* FORMULARIO 2: REGISTRO */}
            {activeTab === 'register' && (
              <form onSubmit={handleRegisterSubmit} className="flex flex-col gap-4">
                <div className="bg-primary/5 p-3 rounded-lg flex gap-2.5 items-start">
                  <span className="material-symbols-outlined text-primary text-[18px] shrink-0 mt-0.5">
                    verified_user
                  </span>
                  <p className="font-body-sm text-body-sm text-on-surface">
                    Las credenciales se activarán tras la validación de Contraloría Interna bajo estándares RBAC.
                  </p>
                </div>

                <div className="flex flex-col gap-1">
                  <label htmlFor="reg-name" className="font-label-sm text-label-sm text-on-surface-variant">
                    NOMBRE COMPLETO
                  </label>
                  <div className="relative flex items-center">
                    <span className="material-symbols-outlined absolute left-3 text-secondary text-[18px]">
                      person
                    </span>
                    <input
                      id="reg-name"
                      type="text"
                      required
                      placeholder="ej. Carlos Mendoza P."
                      value={registerData.fullName}
                      onChange={(e) => setRegisterData({ ...registerData, fullName: e.target.value })}
                      className="w-full bg-surface-container-low focus:bg-surface-container-lowest text-on-surface font-body-md text-body-md pl-10 pr-3 py-2 rounded-lg focus:outline-none"
                    />
                  </div>
                </div>

                <div className="flex flex-col gap-1">
                  <label htmlFor="reg-email" className="font-label-sm text-label-sm text-on-surface-variant">
                    EMAIL INSTITUCIONAL
                  </label>
                  <input
                    id="reg-email"
                    type="email"
                    required
                    placeholder="c.mendoza@fyag.cl"
                    value={registerData.email}
                    onChange={(e) => setRegisterData({ ...registerData, email: e.target.value })}
                    className="w-full bg-surface-container-low focus:bg-surface-container-lowest text-on-surface font-body-md text-body-md px-3 py-2 rounded-lg focus:outline-none"
                  />
                </div>

                <div className="flex flex-col gap-1">
                  <label htmlFor="reg-password" className="font-label-sm text-label-sm text-on-surface-variant">
                    CREAR CONTRASEÑA
                  </label>
                  <div className="relative flex items-center">
                    <span className="material-symbols-outlined absolute left-3 text-secondary text-[18px]">
                      key
                    </span>
                    <input
                      id="reg-password"
                      type={showRegPassword ? 'text' : 'password'}
                      required
                      placeholder="••••••••••••"
                      value={registerData.password}
                      onChange={(e) => setRegisterData({ ...registerData, password: e.target.value })}
                      className="w-full bg-surface-container-low focus:bg-surface-container-lowest text-on-surface font-body-md text-body-md pl-10 pr-10 py-2 rounded-lg focus:outline-none transition-colors"
                    />
                    <button
                      type="button"
                      onClick={() => setShowRegPassword(!showRegPassword)}
                      className="absolute right-2 p-1 text-secondary hover:text-on-surface"
                    >
                      <span className="material-symbols-outlined text-[18px]">
                        {showRegPassword ? 'visibility_off' : 'visibility'}
                      </span>
                    </button>
                  </div>
                </div>

                <div className="flex flex-col gap-1">
                  <label htmlFor="reg-password-confirm" className="font-label-sm text-label-sm text-on-surface-variant">
                    CONFIRMAR CONTRASEÑA
                  </label>
                  <div className="relative flex items-center">
                    <span className="material-symbols-outlined absolute left-3 text-secondary text-[18px]">
                      lock
                    </span>
                    <input
                      id="reg-password-confirm"
                      type={showRegConfirmPassword ? 'text' : 'password'}
                      required
                      placeholder="••••••••••••"
                      value={registerData.confirmPassword}
                      onChange={(e) => setRegisterData({ ...registerData, confirmPassword: e.target.value })}
                      className="w-full bg-surface-container-low focus:bg-surface-container-lowest text-on-surface font-body-md text-body-md pl-10 pr-10 py-2 rounded-lg focus:outline-none transition-colors"
                    />
                    <button
                      type="button"
                      onClick={() => setShowRegConfirmPassword(!showRegConfirmPassword)}
                      className="absolute right-2 p-1 text-secondary hover:text-on-surface"
                    >
                      <span className="material-symbols-outlined text-[18px]">
                        {showRegConfirmPassword ? 'visibility_off' : 'visibility'}
                      </span>
                    </button>
                  </div>
                </div>

                <div className="flex flex-col gap-1">
                  <label htmlFor="reg-role" className="font-label-sm text-label-sm text-on-surface-variant">
                    ROL SOLICITADO
                  </label>
                  <select
                    id="reg-role"
                    value={registerData.role}
                    onChange={(e) => setRegisterData({ ...registerData, role: e.target.value })}
                    className="w-full bg-surface-container-low focus:bg-surface-container-lowest text-on-surface font-body-md text-body-md px-3 py-2 rounded-lg focus:outline-none"
                  >
                    <option value="operaciones">Técnico de Terreno</option>
                    <option value="supervisor">Supervisor de Obra</option>
                    <option value="finanzas">Control Presupuestario</option>
                    <option value="adquisiciones">Gestión Bodega / Insumos</option>
                  </select>
                </div>

                <button
                  type="submit"
                  className="w-full mt-2 bg-primary-container hover:bg-primary text-on-primary font-headline-sm text-headline-sm py-2.5 rounded-lg shadow-md hover:shadow-lg transition-all flex items-center justify-center gap-2"
                >
                  <span className="material-symbols-outlined text-[20px]">send</span>
                  <span>Enviar Solicitud a Gerencia</span>
                </button>
              </form>
            )}

            {/* Footer */}
            <footer className="pt-4 mt-2 flex flex-col gap-3">
              <div className="flex items-center justify-between text-secondary pt-2">
                <span className="font-label-sm text-[10px]">FLYAG - FRÍO Y AGROINDUSTRIA</span>
              </div>
            </footer>
          </div>
        </div>
      </div>
    </main>
  );
}
