import { useState } from 'react';
import flyagLogo from '../assets/flyag-logo-pag.png';

export default function Auth({ onLoginSuccess }) {
  const [email, setEmail] = useState('c.araya@fyag.cl');
  const [password, setPassword] = useState('');
  const [mensaje, setMensaje] = useState('');
  const handleLoginSubmit = async (event) => {
    event.preventDefault();
    // Integrar aquí la validación de credenciales y emisión JWT del backend.
    setMensaje('La validación JWT requiere conexión con el servicio institucional.');
  };
  return <main className="w-full max-w-md mx-auto"><section className="rounded-xl bg-surface-container-lowest p-6 shadow-xl md:p-8"><header className="mb-6 text-center"><img alt="Logo FLYAG" className="mx-auto mb-5 h-16 w-auto object-contain" src={flyagLogo} /><div className="rounded-lg bg-surface-container-low p-4 text-left"><h1 className="font-headline-sm text-headline-sm font-bold text-on-surface">ERP Obras &amp; Presupuestos</h1><p className="mt-1 text-body-sm text-secondary">Acceso institucional FYAG · RBAC activo</p></div></header>
    <form onSubmit={handleLoginSubmit} className="flex flex-col gap-4"><label className="flex flex-col gap-1.5 text-label-sm font-semibold text-on-surface-variant">CORREO INSTITUCIONAL<input type="email" required placeholder="usuario@fyag.cl" value={email} onChange={(event) => setEmail(event.target.value)} className="rounded-lg bg-surface-container-low px-3 py-2.5 text-body-md font-normal text-on-surface focus:bg-surface-container-lowest focus:outline-none" /></label><label className="flex flex-col gap-1.5 text-label-sm font-semibold text-on-surface-variant">CONTRASEÑA DE ACCESO<input type="password" required value={password} onChange={(event) => setPassword(event.target.value)} className="rounded-lg bg-surface-container-low px-3 py-2.5 text-body-md font-normal text-on-surface focus:bg-surface-container-lowest focus:outline-none" /></label><button type="submit" className="mt-2 flex items-center justify-center gap-2 rounded-lg bg-primary-container py-2.5 font-semibold text-on-primary hover:bg-primary"><span className="material-symbols-outlined">lock_open</span>Ingresar al ERP FYAG</button>{mensaje && <p role="status" className="text-body-sm text-secondary">{mensaje}</p>}</form>
    <button type="button" onClick={() => setMensaje('La activación se realiza mediante la invitación institucional enviada por Gerencia.')} className="mt-5 w-full text-center text-label-md font-semibold text-primary hover:underline">¿Recibió una invitación institucional? Activar Cuenta</button><footer className="mt-8 border-t border-surface-container pt-4 text-center text-[10px] text-secondary">FLYAG - FRÍO Y AGROINDUSTRIA</footer>
  </section></main>;
}
