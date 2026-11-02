import React,{useEffect,useState} from 'react';
import {Alert,Empty,Spin,Statistic} from 'antd';
import api from '../api/client';
import CourseCard from './CourseCard';
import {useApp} from '../state/AppContext';
export default function HotCourses(){
  const {meta}=useApp();const [data,setData]=useState(null);const [error,setError]=useState('');
  useEffect(()=>{api.get('/hot-courses?limit=12').then(setData).catch(e=>setError(e.message));},[]);
  return <section><div className="section-heading"><div><h2>热门课程参考</h2><p>从关注较多的教师所授课程开始了解。</p></div></div>
    <div className="summary-grid"><Statistic title="不同课程名称" value={meta?.summary.courses ?? '—'}/><Statistic title="课程—教师记录" value={meta?.summary.offerings ?? '—'}/>
      <Statistic title="已唯一关联教师" value={meta?.summary.teachers ?? '—'}/><Statistic title="记录平均历史GPA" value={meta?.summary.avg_gpa} precision={2}/></div>
    {error?<Alert type="error" message={error}/>:!data?<Spin/>:<><p className="muted">{data.basis}</p><div className="course-grid">{data.courses.map(c=><CourseCard key={c.offering_id} course={c}/>)}</div>{!data.courses.length&&<Empty/>}</>}
  </section>;
}
