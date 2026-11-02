import React from 'react';
import { Button, Badge, Space } from 'antd';
import { BookOutlined, HeartOutlined, UserOutlined, SwapOutlined } from '@ant-design/icons';
import { useApp } from '../state/AppContext';
export default function Header(){
  const app=useApp();
  return <header className="brand-header"><div className="brand"><span className="brand-icon"><BookOutlined/></span>
    <div><h1>浙大小先生</h1><p>让选课有据可依</p></div></div>
    <Space wrap><Button icon={<UserOutlined/>} onClick={()=>app.setShowPreference(true)}>我的偏好</Button>
      <Button icon={<SwapOutlined/>} onClick={()=>app.setShowCompare(true)}>课程比较 ({app.comparison.length})</Button>
      <Badge count={app.shortlist.items.length} size="small"><Button icon={<HeartOutlined/>} onClick={()=>app.setShowShortlist(true)}>自选清单</Button></Badge>
    </Space></header>;
}
