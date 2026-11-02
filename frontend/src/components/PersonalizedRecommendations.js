import React,{useEffect,useState} from 'react';
import {Alert,Button,Empty,Spin,Tag} from 'antd';
import api from '../api/client';
import {useApp} from '../state/AppContext';
import CourseCard from './CourseCard';
export default function PersonalizedRecommendations(){
  const {profileVersion,setShowPreference}=useApp();const [refresh,setRefresh]=useState(0);const [data,setData]=useState(null);const [error,setError]=useState('');const [busy,setBusy]=useState(false);
  useEffect(()=>{let active=true;setBusy(true);setError('');api.post('/personalized-recommendations',{limit:12}).then(r=>{if(active)setData(r);})
    .catch(e=>{if(active)setError(e.message);}).finally(()=>{if(active)setBusy(false);});return()=>{active=false;};},[profileVersion,refresh]);
  return <section><div className="section-heading"><div><h2>为你整理的候选</h2><p>显式兴趣与条件优先，浏览记录辅助排序。</p></div><div><Button onClick={()=>setShowPreference(true)}>修改偏好</Button> <Button onClick={()=>setRefresh(v=>v+1)}>刷新推荐</Button></div></div>
    <div className="preference-summary">我的兴趣：{data?.preferences.interests.length?data.preferences.interests.map(t=><Tag key={t}>{t}</Tag>):'尚未设置'}
      <span className="muted"> · 已记录浏览 {data?.insights.view_count||0} 次</span></div>
    {error?<Alert type="error" message={error}/>:<Spin spinning={busy}><div className="course-grid">{data?.recommendations.map(c=><CourseCard key={c.offering_id} course={c}/>)}</div>
      {data&&!data.recommendations.length&&<Empty description="当前兴趣与条件下没有匹配候选，可自行修改偏好"/>}</Spin>}
  </section>;
}
