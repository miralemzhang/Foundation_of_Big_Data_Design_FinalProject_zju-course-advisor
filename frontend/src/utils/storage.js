export function userId() {
  let id = localStorage.getItem('xiaoxiansheng_user');
  if (!id) {
    id = `u_${window.crypto?.randomUUID?.() || `${Date.now()}_${Math.random().toString(36).slice(2)}`}`;
    localStorage.setItem('xiaoxiansheng_user', id);
  }
  return id;
}
