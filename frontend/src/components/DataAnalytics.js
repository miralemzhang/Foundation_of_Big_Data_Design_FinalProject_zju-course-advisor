import React,{useEffect,useState} from 'react';
import {Alert,Card,Select,Spin,Table} from 'antd';
import {BarChart,Bar,XAxis,YAxis,Tooltip,ResponsiveContainer,PieChart,Pie,Cell} from 'recharts';
import api from '../api/client';
import {numeric} from './CourseCard';
const colors=['#5566cb','#8390e5','#ab90d5','#c2a6df','#65b4bd','#8bc8b3','#c8d9a5','#e3cd9e','#c2c9d8'];
export default function DataAnalytics(){
  const [stats,setStats]=useState(null);const [teachers,setTeachers]=useState({teachers:[],total:0});const [college,setCollege]=useState('');const [page,setPage]=useState(1);const [error,setError]=useState('');
  useEffect(()=>{api.get('/college-stats').then(setStats).catch(e=>setError(e.message));},[]);
  useEffect(()=>{api.get('/teachers',{params:{college,page,page_size:10}}).then(setTeachers).catch(e=>setError(e.message));},[college,page]);
  if(error)return <Alert type="error" message={error}/>;if(!stats)return <Spin/>;
  const rows=Object.entries(stats.stats).map(([name,s])=>({name,...s}));
  const ranked=[...rows].sort((a,b)=>b.offerings-a.offerings);const pie=ranked.slice(0,8).map(r=>({name:r.name,value:r.offerings}));
  if(ranked.length>8)pie.push({name:'其他',value:ranked.slice(8).reduce((s,r)=>s+r.offerings,0)});
  return <section><div className="section-heading"><div><h2>看清数据的分布</h2><p>按教师所在学院分组；历史GPA按有效课程—教师记录计算算术平均。</p></div></div>
    <div className="chart-grid"><Card title="课程—教师记录分布"><ResponsiveContainer width="100%" height={280}><PieChart><Pie data={pie} dataKey="value" nameKey="name" innerRadius={65} outerRadius={105}>{pie.map((r,i)=><Cell key={r.name} fill={colors[i%colors.length]}/>)}</Pie><Tooltip/></PieChart></ResponsiveContainer><p className="small muted">含“其他”，分母为全部 {stats.summary.offerings} 条记录。</p></Card>
      <Card title="记录较多学院的平均历史GPA"><ResponsiveContainer width="100%" height={280}><BarChart data={ranked.slice(0,8)} margin={{bottom:65}}><XAxis dataKey="name" angle={-28} textAnchor="end" interval={0} tick={{fontSize:10}}/><YAxis domain={[0,5]}/><Tooltip/><Bar dataKey="avg_gpa" name="平均历史GPA" fill="#7b83d5"/></BarChart></ResponsiveContainer></Card></div>
    <Card title="相关授课教师" extra={<Select allowClear showSearch style={{width:230}} placeholder="按教师学院筛选" value={college||undefined} onChange={v=>{setCollege(v||'');setPage(1);}} options={rows.filter(r=>r.name!=='教师学院未唯一核实').map(r=>({value:r.name,label:r.name}))}/> }>
      <Table rowKey="id" dataSource={teachers.teachers} pagination={{current:page,total:teachers.total,pageSize:10,showSizeChanger:false,onChange:setPage}} columns={[
        {title:'教师',dataIndex:'name'},{title:'学院',dataIndex:'college'},{title:'教师评分 / 10',dataIndex:'rating',render:v=>numeric(v)},
        {title:'评分人数',dataIndex:'rating_count',render:v=>numeric(v,0)},{title:'原始热度',dataIndex:'heat',render:v=>numeric(v,0)}]}/>
    </Card>
  </section>;
}
