import React from 'react';
import { Card, Button, Space, Tag, Tooltip } from 'antd';
import { useApp } from '../state/AppContext';
export const numeric = (v, digits=2) => v===null || v===undefined ? '—' : Number(v).toFixed(digits);
export default function CourseCard({course}) {
  const app=useApp();
  return <Card className="course-tile" data-testid={`course-${course.offering_id}`}>
    <div className="course-category">{course.categories.map(c=><Tag key={c}>{c}</Tag>)}</div>
    <h3>{course.course_name}</h3>
    <p className="muted">{course.teacher} · {course.college || '教师学院待核实'}</p>
    <div className="course-metrics">
      <Tooltip title="历史统计，不代表个人预期成绩"><span><strong>{numeric(course.avg_gpa)}</strong>历史 GPA</span></Tooltip>
      <Tooltip title="教师级评分，与课程GPA口径不同"><span><strong>{numeric(course.teacher_rating)}</strong>教师评分 / 10</span></Tooltip>
    </div>
    <p className="small muted">GPA来源人数 {course.student_count} · 教师评分人数 {numeric(course.teacher_rating_count,0)}</p>
    {course.recommendation_reason && <p className="reason">{course.recommendation_reason}</p>}
    {course.similarity!==undefined && <p className="small muted">内容相似度 {numeric(course.similarity,3)}（非质量分）</p>}
    <Space wrap>
      <Button size="small" onClick={()=>app.setDetail(course)}>详情与依据</Button>
      <Button size="small" onClick={()=>app.compare(course)}>比较</Button>
      <Button size="small" type="primary" disabled={app.saving} onClick={()=>app.add(course)}>
        {app.shortlist.items.includes(course.offering_id)?'已加入':'加入自选'}</Button>
    </Space>
  </Card>;
}
