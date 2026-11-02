import React, { createContext, useContext, useEffect, useRef, useState } from 'react';
import { message } from 'antd';
import api from '../api/client';
const Context = createContext(null);
export const useApp = () => useContext(Context);
export function AppProvider({children}) {
  const [meta,setMeta] = useState(null);
  const [bootError,setBootError] = useState('');
  const [shortlist,setShortlist] = useState({items:[],courses:[],revision:0});
  const [saving,setSaving] = useState(false);
  const [comparison,setComparison] = useState([]);
  const [detail,setDetail] = useState(null);
  const [showShortlist,setShowShortlist] = useState(false);
  const [showCompare,setShowCompare] = useState(false);
  const [showPreference,setShowPreference] = useState(false);
  const [profileVersion,setProfileVersion] = useState(0);
  const current = useRef(shortlist); current.current=shortlist;
  const busy = useRef(false);
  useEffect(() => {
    Promise.all([api.get('/meta'),api.get('/shortlist')]).then(([m,s])=>{setMeta(m);setShortlist(s);})
      .catch(e=>setBootError(e.message));
    // Remove the former browser-side service credential; the backend now owns it.
    localStorage.removeItem('dashscope_api_key');
  },[]);
  async function saveShortlist(items) {
    if (busy.current) return false;
    busy.current=true;setSaving(true);
    try { const s=await api.put('/shortlist',{items,revision:current.current.revision});current.current=s;setShortlist(s);return true; }
    catch(e) {
      message.error(e.message);
      try {setShortlist(await api.get('/shortlist'));}catch(reload){setBootError(reload.message);}
      return false;
    } finally {busy.current=false;setSaving(false);}
  }
  async function add(course) {
    if(current.current.items.includes(course.offering_id)){message.info('已在自选清单中');return;}
    if(await saveShortlist([...current.current.items,course.offering_id])) {
      message.success('已加入自选清单');
      api.post('/user-behavior',{action_type:'add_shortlist',data:{offering_id:course.offering_id}}).catch(()=>{});
    }
  }
  function compare(course) {
    setComparison(old=>{
      if(old.some(c=>c.offering_id===course.offering_id))return old;
      if(old.length>=3){message.info('最多比较3项，请先移除一项');return old;}
      return [...old,course];
    });setShowCompare(true);
  }
  return <Context.Provider value={{meta,bootError,shortlist,saving,saveShortlist,add,comparison,setComparison,compare,
    detail,setDetail,showShortlist,setShowShortlist,showCompare,setShowCompare,showPreference,setShowPreference,
    profileVersion,profileChanged:()=>setProfileVersion(v=>v+1)}}>{children}</Context.Provider>;
}
