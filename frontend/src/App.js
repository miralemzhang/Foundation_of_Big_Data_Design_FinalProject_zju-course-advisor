import React from 'react';
import { Alert, Tabs } from 'antd';
import Header from './components/Header';
import ChatInterface from './components/ChatInterface';
import CourseSearch from './components/CourseSearch';
import HotCourses from './components/HotCourses';
import PersonalizedRecommendations from './components/PersonalizedRecommendations';
import DataAnalytics from './components/DataAnalytics';
import WorkspaceDrawers from './components/WorkspaceDrawers';
import { AppProvider,useApp } from './state/AppContext';
import './App.css';
function Workspace() {
  const {bootError,meta}=useApp();
  return <div className="app-layout"><Header/><main className="main-container">
    {bootError && <Alert type="error" showIcon message={bootError} description="请检查后端状态后刷新页面。"/>}
    <Tabs defaultActiveKey="chat" className="main-tabs" items={[
      {key:'chat',label:'智能对话',children:<ChatInterface/>},
      {key:'search',label:'课程筛选',children:<CourseSearch/>},
      {key:'recommend',label:'为你推荐',children:<PersonalizedRecommendations/>},
      {key:'hot',label:'热门课程',children:<HotCourses/>},
      {key:'analytics',label:'数据分析',children:<DataAnalytics/>}
    ]}/>
    <footer>{meta?.is_sample?'虚构结构样例（非真实课程评价）':'历史课程资料'} · 数据版本 {meta?.data_version || '加载中'} · 推荐用于整理候选，选课安排以学校当期通知为准</footer>
  </main><WorkspaceDrawers/></div>;
}
export default function App(){return <AppProvider><Workspace/></AppProvider>;}
