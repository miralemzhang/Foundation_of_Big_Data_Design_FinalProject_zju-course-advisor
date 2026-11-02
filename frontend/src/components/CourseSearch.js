import React,{useEffect,useState} from 'react';
import { Alert,Button,Empty,Form,Input,InputNumber,Pagination,Select,Spin } from 'antd';
import api from '../api/client';
import {useApp} from '../state/AppContext';
import CourseCard from './CourseCard';
export default function CourseSearch(){
  const {meta}=useApp();const [spec,setSpec]=useState({query:'',filters:{},page:1,page_size:12,sort:'relevance'});
  const [result,setResult]=useState({results:[],total:0});const [busy,setBusy]=useState(true);const [error,setError]=useState('');
  useEffect(()=>{let active=true;setBusy(true);setError('');api.post('/search',spec)
    .then(r=>{if(active)setResult(r);}).catch(e=>{if(active)setError(e.message);}).finally(()=>{if(active)setBusy(false);});
    return()=>{active=false;};},[spec]);
  function submit(values){
    const {query,sort,...rest}=values;
    const filters=Object.fromEntries(Object.entries(rest).filter(([,v])=>v!==undefined && v!==null && v!=='' && (!Array.isArray(v)||v.length)));
    setSpec({query:query||'',sort:sort||'relevance',filters,page:1,page_size:12});
  }
  return <section><div className="section-heading"><div><h2>找到适合自己的通识课</h2><p>把兴趣与条件放在一起，逐步缩小候选范围。</p></div></div>
    <Form onFinish={submit} layout="vertical" className="filter-surface" initialValues={{sort:'relevance'}}>
      <div className="filter-grid"><Form.Item name="query" label="课程／教师关键词"><Input placeholder="例如：博弈论、蒋文华" allowClear/></Form.Item>
        <Form.Item name="categories" label="通识类别"><Select mode="multiple" allowClear placeholder="不限类别" options={(meta?.categories||[]).map(v=>({value:v,label:v}))}/></Form.Item>
        <Form.Item name="min_gpa" label="历史GPA下限"><InputNumber min={0} max={5} step={0.1} placeholder="不限"/></Form.Item>
        <Form.Item name="max_gpa" label="历史GPA上限"><InputNumber min={0} max={5} step={0.1} placeholder="不限"/></Form.Item>
        <Form.Item name="min_teacher_rating" label="教师评分下限（0–10）"><InputNumber min={0} max={10} step={0.1} placeholder="不限"/></Form.Item>
        <Form.Item name="max_teacher_rating" label="教师评分上限（0–10）"><InputNumber min={0} max={10} step={0.1} placeholder="不限"/></Form.Item>
        <Form.Item name="min_teacher_rating_count" label="教师评分人数下限"><InputNumber min={0} precision={0} placeholder="不限"/></Form.Item>
        <Form.Item name="min_students" label="GPA来源人数下限"><InputNumber min={0} precision={0} placeholder="不限"/></Form.Item>
        <Form.Item name="college" label="教师所在学院"><Select allowClear showSearch placeholder="不限" options={(meta?.colleges||[]).map(v=>({value:v,label:v}))}/></Form.Item>
        <Form.Item name="sort" label="排序"><Select options={[{value:'relevance',label:'关键词相关'},{value:'gpa',label:'历史GPA'},{value:'rating',label:'教师评分'},{value:'popularity',label:'教师评分人数'}]}/></Form.Item>
      </div><Button htmlType="submit" type="primary" loading={busy}>筛选课程</Button>
      <span className="small muted filter-note">未能唯一关联的教师评分不参与评分筛选；500+保留为截断人数。</span>
    </Form>
    {error?<Alert type="error" showIcon message={error}/>:<Spin spinning={busy}><p className="result-count">共 {result.total} 条课程—教师记录</p>
      <div className="course-grid">{result.results.map(c=><CourseCard key={c.offering_id} course={c}/>)}</div>
      {!busy&&!result.results.length&&<Empty description="没有符合条件的课程，可自行修改筛选条件"/>}
      <Pagination current={spec.page} pageSize={12} total={result.total} showSizeChanger={false} onChange={page=>setSpec(s=>({...s,page}))}/>
    </Spin>}
  </section>;
}
