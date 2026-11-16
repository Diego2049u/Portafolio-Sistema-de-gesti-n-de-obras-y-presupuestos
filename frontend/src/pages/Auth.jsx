import { useState } from 'react';
import flyagLogo from '../assets/flyag-logo-pag.png';
import { api } from '../api/client';

export default function Auth({ onLoginSuccess }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [mensaje, setMensaje] = useState('');
  const [enviando, setEnviando] = useState(false);
  const handleLoginSubmit = async (event) => {
    event.preventDefault();
    setMensaje('');
    setEnviando(true);
    try {
      const respuesta = await api.auth.login({ email: email.trim(), password });
      onLoginSuccess(respuesta.user);
    } catch (error) {
      setMensaje(error.message || 'No se pudo iniciar sesión. Inténtalo nuevamente.');
    } finally {
      setEnviando(false);
    }
  };
  return <main className="w-full max-w-md mx-auto"><section className="rounded-xl bg-surface-container-lowest p-6 shadow-xl md:p-8"><header className="mb-6 text-center"><img alt="Logo FLYAG" className="mx-auto mb-5 h-16 w-auto object-contain" src={flyagLogo} /><div className="rounded-lg bg-surface-container-low p-4 text-left"><h1 className="font-headline-sm text-headline-sm font-bold text-on-surface">ERP Obras &amp; Presupuestos</h1><p className="mt-1 text-body-sm text-secondary">Acceso institucional FYAG · RBAC activo</p></div></header>
    <form onSubmit={handleLoginSubmit} className="flex flex-col gap-4"><label className="flex flex-col gap-1.5 text-label-sm font-semibold text-on-surface-variant">CORREO INSTITUCIONAL<input type="email" autoComplete="username" required placeholder="usuario@fyag.cl" value={email} onChange={(event) => setEmail(event.target.value)} className="rounded-lg bg-surface-container-low px-3 py-2.5 text-body-md font-normal text-on-surface focus:bg-surface-container-lowest focus:outline-none" /></label><label className="flex flex-col gap-1.5 text-label-sm font-semibold text-on-surface-variant">CONTRASEÑA DE ACCESO<input type="password" autoComplete="current-password" required value={password} onChange={(event) => setPassword(event.target.value)} className="rounded-lg bg-surface-container-low px-3 py-2.5 text-body-md font-normal text-on-surface focus:bg-surface-container-lowest focus:outline-none" /></label><button disabled={enviando} type="submit" className="mt-2 flex items-center justify-center gap-2 rounded-lg bg-primary-container py-2.5 font-semibold text-on-primary hover:bg-primary disabled:cursor-wait disabled:opacity-60"><span className="material-symbols-outlined">{enviando ? 'progress_activity' : 'lock_open'}</span>{enviando ? 'Conectando…' : 'Ingresar al ERP FYAG'}</button>{mensaje && <p role="alert" className="text-body-sm text-error">{mensaje}</p>}</form>
    <button type="button" onClick={() => setMensaje('La activación se realiza mediante la invitación institucional enviada por Gerencia.')} className="mt-5 w-full text-center text-label-md font-semibold text-primary hover:underline">¿Recibió una invitación institucional? Activar Cuenta</button><footer className="mt-8 border-t border-surface-container pt-4 text-center text-[10px] text-secondary">FLYAG - FRÍO Y AGROINDUSTRIA</footer>
  </section></main>;
}
