import React,{useEffect,useRef,useState} from 'react';
import { Alert,Button,Collapse,Input,Space,Spin,Tag } from 'antd';
import { SendOutlined,PlusOutlined } from '@ant-design/icons';
import api from '../api/client';
import CourseCard from './CourseCard';
function referenceAnswer(result){
  const refs=new Map((result.evidence||[]).map((e,i)=>[e.evidence_id,i+1]));
  return (result.answer||'').replace(/\[([^\]]+)\]/g,(whole,id)=>refs.has(id)?`[${refs.get(id)}]`:whole);
}
function Evidence({rows}){return <div className="evidence-list">{rows.map((e,i)=><article key={e.evidence_id}>
  <strong>[{i+1}] {e.kind==='comment'||e.scope==='teacher'?'教师级资料':'历史统计资料'}</strong>
  <p>{e.content}</p><small>{typeof e.source==='string'?e.source:JSON.stringify(e.source)}</small>
</article>)}</div>;}
const suggestions=['查询示例教师甲《策略博弈入门（示例）》的GPA和评价依据','找历史GPA至少4.3的文艺审美类通识课','找与《策略博弈入门（示例）》相似的其他课程'];
export default function ChatInterface(){
  const [sid,setSid]=useState(localStorage.getItem('xiaoxiansheng_session'));
  const [turns,setTurns]=useState([]);const [input,setInput]=useState('');const [busy,setBusy]=useState(false);
  const [restoring,setRestoring]=useState(true);const [constraints,setConstraints]=useState({});const [query,setQuery]=useState('');const [restoreError,setRestoreError]=useState('');
  const conversation=useRef(null);
  useEffect(()=>{if(conversation.current)conversation.current.scrollTop=conversation.current.scrollHeight;},[turns,restoring]);
  useEffect(()=>{
    const saved=localStorage.getItem('xiaoxiansheng_session');
    if(!saved){setRestoring(false);return;}
    api.get(`/sessions/${saved}`).then(s=>{setTurns(s.turns||[]);setConstraints(s.filters);setQuery(s.query);})
      .catch(e=>{if(e.response?.status===404){setSid(null);localStorage.removeItem('xiaoxiansheng_session');}else setRestoreError(e.message);})
      .finally(()=>setRestoring(false));
  },[]);
  async function send(text=input){
    const prompt=text.trim();if(!prompt||busy||restoring)return;
    setBusy(true);setInput('');setTurns(old=>[...old,{prompt,result:null}]);
    try {
      const r=await api.post('/chat',{prompt,session_id:sid});setSid(r.session_id);localStorage.setItem('xiaoxiansheng_session',r.session_id);
      setTurns(old=>[...old.slice(0,-1),{prompt,result:r}]);setConstraints(r.effective_constraints||{});setQuery(r.query||'');
    } catch(e){
      const r=e.response?.data;
      if(r?.session_id){setSid(r.session_id);localStorage.setItem('xiaoxiansheng_session',r.session_id);}
      setTurns(old=>[...old.slice(0,-1),{prompt,result:{...(r||{}),status:'failed',answer:e.message}}]);
    } finally {setBusy(false);}
  }
  async function reset(){
    try{if(sid)await api.delete(`/sessions/${sid}`);setSid(null);localStorage.removeItem('xiaoxiansheng_session');setTurns([]);setConstraints({});setQuery('');}
    catch(e){setRestoreError(e.message);}
  }
  return <section className="chat-workspace"><div className="section-heading"><div><h2>把你的选课想法告诉小先生</h2><p>筛选、比较、找相似课程，也能接着调整条件。</p></div>
    <Button aria-label="新对话" icon={<PlusOutlined/>} disabled={busy||restoring} onClick={reset}>新对话</Button></div>
    <div className="constraint-strip"><span>当前条件</span>{query&&<Tag color="blue">兴趣／查询：{query}</Tag>}
      {Object.entries(constraints).map(([k,v])=><Tag key={k}>{({min_gpa:'GPA≥',max_gpa:'GPA≤',min_teacher_rating:'教师评分≥',max_teacher_rating:'教师评分≤',min_teacher_rating_count:'教师评分人数≥',min_students:'GPA来源人数≥',categories:'类别：',college:'教师学院：'})[k]||k}{Array.isArray(v)?v.join('、'):v}</Tag>)}
      {!query&&!Object.keys(constraints).length&&<span className="muted">尚未设置</span>}</div>
    {restoreError&&<Alert type="error" showIcon closable message={restoreError}/>}
    <Spin spinning={restoring}><div ref={conversation} className="conversation" aria-live="polite">
      {!turns.length&&<div className="chat-welcome"><div className="welcome-symbol">小</div><h3>从一个具体需求开始</h3><p>例如，给定历史GPA要求，再看看内容与你的兴趣是否相近。</p>
        <Space direction="vertical">{suggestions.map(s=><Button key={s} disabled={restoring} onClick={()=>send(s)}>{s}</Button>)}</Space></div>}
      {turns.map((t,i)=><div className="turn" key={i}><div className="user-bubble">{t.prompt}</div>
        {!t.result?<div className="assistant-bubble"><Spin size="small"/> 正在查询课程并核对依据…</div>:<div className="assistant-bubble">
          {t.result.status==='failed'?<Alert type="error" showIcon message={t.result.answer}/>:<div className="answer-text">{referenceAnswer(t.result)}</div>}
          {['verified_template','structured_data'].includes(t.result.answer_mode)&&<Tag>按核验数据整理</Tag>}
          {!!t.result.courses?.length&&<div className="course-grid chat-courses">{t.result.courses.map(c=><CourseCard key={c.offering_id} course={c}/>)}</div>}
          {!!t.result.evidence?.length&&<Collapse size="small" items={[{key:'evidence',label:`查看本轮依据（${t.result.evidence.length}）`,children:<Evidence rows={t.result.evidence}/>}]} />}
          {!!t.result.tool_calls?.length&&<div className="trace-line">实际使用：{t.result.tool_calls.map((t,n)=><Tag key={n} color={t.status==='failed'?'error':'default'}>{t.name}</Tag>)}</div>}
          {t.result.duration_ms!==undefined&&<p className="small muted">耗时 {(t.result.duration_ms/1000).toFixed(1)} 秒 · 请求 {t.result.request_id?.slice(0,8)}{t.result.usage&&` · ${t.result.usage.prompt_tokens+t.result.usage.completion_tokens} tokens${t.result.usage.complete?'':'（部分用量）'}`}</p>}
        </div>}</div>)}
    </div></Spin>
    <div className="composer"><Input.TextArea value={input} onChange={e=>setInput(e.target.value)} autoSize={{minRows:2,maxRows:6}} maxLength={2000}
      placeholder="例如：换成生物方向，GPA要求保持不变。Enter发送，Shift+Enter换行。" aria-label="选课需求"
      onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.nativeEvent.isComposing){e.preventDefault();send();}}}/>
      <Button aria-label="发送" type="primary" icon={<SendOutlined/>} loading={busy} disabled={!input.trim()||restoring} onClick={()=>send()}>发送</Button></div>
  </section>;
}
