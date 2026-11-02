import React,{useEffect,useRef,useState} from 'react';
import {Alert,Button,Descriptions,Drawer,Empty,Form,Input,InputNumber,List,Pagination,Select,Space,Spin,Table,Tag,message} from 'antd';
import {ArrowUpOutlined,ArrowDownOutlined,DeleteOutlined,HolderOutlined} from '@ant-design/icons';
import {useApp} from '../state/AppContext';
import api from '../api/client';
import {numeric} from './CourseCard';

function Detail(){
  const {detail,setDetail}=useApp();const [data,setData]=useState(null);const [page,setPage]=useState(1);const [query,setQuery]=useState('');const [error,setError]=useState('');const [busy,setBusy]=useState(false);
  const oid=detail?.offering_id;
  useEffect(()=>{if(oid){setPage(1);setQuery('');setData(null);api.get(`/courses/${oid}`).catch(e=>setError(e.message));}},[oid]);
  useEffect(()=>{
    if(!oid)return;let active=true;setBusy(true);setError('');api.get(`/courses/${oid}/evidence`,{params:{page,query,limit:8}})
      .then(r=>{if(active)setData(r);}).catch(e=>{if(active)setError(e.message);}).finally(()=>{if(active)setBusy(false);});return()=>{active=false;};
  },[oid,page,query]);
  return <Drawer title={detail?.course_name||'课程详情'} open={!!detail} onClose={()=>setDetail(null)} width={650}>
    {detail&&<><p>{detail.teacher} · {detail.college||'教师学院待核实'}</p><Space wrap>{detail.categories.map(t=><Tag key={t}>{t}</Tag>)}</Space>
      <Descriptions size="small" bordered column={2} className="detail-stats" items={[
        {key:'gpa',label:'历史GPA',children:numeric(detail.avg_gpa)},{key:'count',label:'GPA来源人数',children:detail.student_count},
        {key:'rating',label:'教师评分 / 10',children:numeric(detail.teacher_rating)},{key:'votes',label:'教师评分人数',children:numeric(detail.teacher_rating_count,0)},
        {key:'std',label:'GPA标准差',children:numeric(detail.std_dev)},{key:'comments',label:'教师评论条数',children:detail.comment_count}]}/>
      {detail.teacher_match!=='unique'&&<Alert type="info" showIcon message="该姓名未唯一关联教师记录，未附加教师评分和评论。"/>}
    </>}
    {error&&<Alert type="error" message={error}/>}
    <h3>查看原始依据</h3><Input.Search allowClear placeholder="在教师评论中查找，如：作业" onSearch={v=>{setQuery(v);setPage(1);}}/>
    <Spin spinning={busy}><div className="evidence-list">{data?.evidence.map(e=><article key={e.evidence_id}>
      <Tag>{e.scope==='teacher'?'教师级资料':'课程—教师统计'}</Tag><p>{e.content}</p><small>{e.date&&`${e.date} · `}{typeof e.source==='string'?e.source:JSON.stringify(e.source)}</small>
    </article>)}</div></Spin>
    {data&&<><p className="small muted">评论是个人观点，不自动代表具体课程或当前授课情况。</p><Pagination size="small" current={page} total={data.matching_comments} pageSize={8} showSizeChanger={false} onChange={setPage}/></>}
  </Drawer>;
}

function Shortlist(){
  const app=useApp();const drag=useRef(null);
  function move(from,to){
    if(from===to||from<0||to<0||to>=app.shortlist.items.length||app.saving)return;
    const items=[...app.shortlist.items];const [item]=items.splice(from,1);items.splice(to,0,item);app.saveShortlist(items);
  }
  return <Drawer title="我的自选清单" open={app.showShortlist} onClose={()=>app.setShowShortlist(false)} width={480}>
    <p className="muted">拖拽调整优先级，也可用上下按钮。修改后自动保存到本机。</p>
    <p role="status">{app.saving?'正在保存…':'已保存'} · {app.shortlist.items.length} 项</p>
    {!!app.shortlist.unavailable_items?.length&&<Alert type="info" message="部分历史候选已不在当前数据版本中，可清空后重新加入。"/>}
    {!app.shortlist.items.length&&<Empty description="从课程卡片加入你感兴趣的课程"/>}
    <div className="shortlist-items">{app.shortlist.courses.map(c=>{
      const i=app.shortlist.items.indexOf(c.offering_id);
      return <div className="shortlist-item" key={c.offering_id} draggable={!app.saving} data-testid={`shortlist-${c.offering_id}`}
        onDragStart={e=>{drag.current=i;e.dataTransfer.setData('text/plain',String(i));e.dataTransfer.effectAllowed='move';}}
        onDragOver={e=>e.preventDefault()} onDrop={e=>{e.preventDefault();if(drag.current!==null)move(drag.current,i);drag.current=null;}} onDragEnd={()=>{drag.current=null;}}>
        <HolderOutlined/><span className="rank">{i+1}</span><div className="shortlist-name"><strong>{c.course_name}</strong><p>{c.teacher} · GPA {numeric(c.avg_gpa)}</p></div>
        <Space size={2}><Button aria-label={`上移${c.course_name}`} size="small" icon={<ArrowUpOutlined/>} disabled={i===0||app.saving} onClick={()=>move(i,i-1)}/>
          <Button aria-label={`下移${c.course_name}`} size="small" icon={<ArrowDownOutlined/>} disabled={i===app.shortlist.items.length-1||app.saving} onClick={()=>move(i,i+1)}/>
          <Button aria-label={`移除${c.course_name}`} size="small" icon={<DeleteOutlined/>} disabled={app.saving} onClick={()=>app.saveShortlist(app.shortlist.items.filter(id=>id!==c.offering_id))}/></Space>
      </div>;
    })}</div>
    {!!app.shortlist.items.length&&<Button danger disabled={app.saving} onClick={()=>app.saveShortlist([])}>清空清单</Button>}
    <p className="small muted">清单用于整理优先顺序，不会替你提交学校选课系统。</p>
  </Drawer>;
}

function Compare(){
  const app=useApp();const [data,setData]=useState(null);const [error,setError]=useState('');const [busy,setBusy]=useState(false);
  const ids=app.comparison.map(c=>c.offering_id).join(',');
  useEffect(()=>{
    if(!app.showCompare||ids.split(',').filter(Boolean).length<2){setData(null);return;}
    let active=true;setBusy(true);setError('');api.post('/compare',{offering_ids:ids.split(',')}).then(r=>{if(active)setData(r);})
      .catch(e=>{if(active)setError(e.message);}).finally(()=>{if(active)setBusy(false);});return()=>{active=false;};
  },[app.showCompare,ids]);
  const rows=[['teacher','教师'],['avg_gpa','历史GPA'],['teacher_rating','教师评分 / 10'],['teacher_rating_count','教师评分人数'],['student_count','GPA来源人数'],['comment_count','教师评论条数']];
  return <Drawer title="课程比较" open={app.showCompare} onClose={()=>app.setShowCompare(false)} width={900}>
    <Space wrap>{app.comparison.map(c=><Tag closable key={c.offering_id} onClose={()=>app.setComparison(old=>old.filter(v=>v.offering_id!==c.offering_id))}>{c.course_name} · {c.teacher}</Tag>)}</Space>
    {app.comparison.length<2?<Empty description="从课程卡片选择2–3项进行比较"/>:<Spin spinning={busy}>
      {error&&<Alert type="error" message={error}/>}<Table className="comparison-table" pagination={false} rowKey="field" dataSource={rows.map(([field,label])=>({field,label}))} columns={[
        {title:'比较维度',dataIndex:'label',width:135},...app.comparison.map(c=>({title:c.course_name,key:c.offering_id,render:(_,r)=>{
          const v=c[r.field];return ['avg_gpa','teacher_rating'].includes(r.field)?numeric(v):v??'暂无资料';
        }}))]}/>
      {data?.details.map(d=><section className="compare-evidence" key={d.course.offering_id}><h3>{d.course.course_name} · {d.course.teacher}</h3>
        {d.evidence.filter(e=>e.kind==='comment').length?<List size="small" dataSource={d.evidence.filter(e=>e.kind==='comment')} renderItem={e=><List.Item><div><p>{e.content}</p><small className="muted">教师级评价 · {e.source}</small></div></List.Item>}/>:<p>暂无可唯一关联的教师评论。</p>}
        <Button size="small" onClick={()=>app.setDetail(d.course)}>查看完整依据</Button></section>)}
      <p className="muted">教师级评价不自动归于具体课程；不同指标口径分开比较。</p>
    </Spin>}
  </Drawer>;
}

function Preferences(){
  const app=useApp();const [form]=Form.useForm();const [busy,setBusy]=useState(false);const [error,setError]=useState('');
  useEffect(()=>{if(app.showPreference){setBusy(true);setError('');api.get('/profile').then(r=>form.setFieldsValue({interests:r.profile.interests,...r.profile.filters}))
    .catch(e=>setError(e.message)).finally(()=>setBusy(false));}},[app.showPreference,form]);
  async function save(values){
    setBusy(true);setError('');
    try{const {interests,...rest}=values;const filters=Object.fromEntries(Object.entries(rest).filter(([,v])=>v!==undefined&&v!==null));
      await api.put('/profile',{interests:interests||[],filters});app.profileChanged();message.success('偏好已保存');app.setShowPreference(false);
    }catch(e){setError(e.message);}finally{setBusy(false);}
  }
  return <Drawer title="我的选课偏好" open={app.showPreference} onClose={()=>app.setShowPreference(false)} width={450}>
    <p className="muted">你明确设置的条件优先。新对话会使用这里的筛选条件，已有对话保持自身状态。</p>{error&&<Alert type="error" message={error}/>}
    <Form form={form} layout="vertical" onFinish={save} disabled={busy}>
      <Form.Item name="interests" label="兴趣方向"><Select mode="tags" placeholder="输入兴趣，回车添加" options={['历史','生物','艺术','经济'].map(value=>({value,label:value}))}/></Form.Item>
      <Form.Item name="min_gpa" label="历史GPA下限"><InputNumber min={0} max={5} step={0.1}/></Form.Item>
      <Form.Item name="max_gpa" label="历史GPA上限"><InputNumber min={0} max={5} step={0.1}/></Form.Item>
      <Form.Item name="min_teacher_rating" label="教师评分下限（0–10）"><InputNumber min={0} max={10} step={0.1}/></Form.Item>
      <Form.Item name="max_teacher_rating" label="教师评分上限（0–10）"><InputNumber min={0} max={10} step={0.1}/></Form.Item>
      <Form.Item name="min_teacher_rating_count" label="教师评分人数下限"><InputNumber min={0} precision={0}/></Form.Item>
      <Space><Button type="primary" htmlType="submit" loading={busy}>保存偏好</Button><Button onClick={()=>{form.resetFields();save({interests:[]});}}>清空显式偏好</Button></Space>
    </Form>
  </Drawer>;
}
export default function WorkspaceDrawers(){return <><Detail/><Shortlist/><Compare/><Preferences/></>;}
