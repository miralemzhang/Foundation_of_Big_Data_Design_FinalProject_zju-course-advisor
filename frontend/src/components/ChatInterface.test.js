import React from 'react';
import {render,screen,fireEvent,waitFor} from '@testing-library/react';
import ChatInterface from './ChatInterface';
import api from '../api/client';
jest.mock('../api/client',()=>({get:jest.fn(),post:jest.fn(),delete:jest.fn()}));
jest.mock('./CourseCard',()=>({course})=><div>{course.course_name}</div>);
beforeEach(()=>{localStorage.clear();jest.clearAllMocks();});
test('sends session-aware requests without exposing a service key',async()=>{
  api.post.mockResolvedValue({session_id:'session_one',status:'completed',answer:'已查询',courses:[],evidence:[],effective_constraints:{min_gpa:4},query:'生物'});
  render(<ChatInterface/>);fireEvent.change(screen.getByLabelText('选课需求'),{target:{value:'生物方向，GPA至少4'}});fireEvent.click(screen.getByRole('button',{name:'发送'}));
  await screen.findByText('已查询');expect(api.post).toHaveBeenCalledWith('/chat',{prompt:'生物方向，GPA至少4',session_id:null});
  expect(localStorage.getItem('xiaoxiansheng_session')).toBe('session_one');expect(screen.getByText('GPA≥4')).toBeInTheDocument();
});
test('restores saved turns with course cards then clears only the conversation',async()=>{
  localStorage.setItem('xiaoxiansheng_session','saved');api.get.mockResolvedValue({turns:[{prompt:'旧问题',result:{answer:'旧回答',courses:[{offering_id:'x',course_name:'博弈论基础'}]}}],filters:{min_gpa:4},query:''});api.delete.mockResolvedValue({});
  render(<ChatInterface/>);await screen.findByText('旧回答');expect(screen.getByText('博弈论基础')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button',{name:'新对话'}));await waitFor(()=>expect(localStorage.getItem('xiaoxiansheng_session')).toBeNull());
  expect(api.delete).toHaveBeenCalledWith('/sessions/saved');expect(api.post).not.toHaveBeenCalled();
});
test('shows model timeout as an error rather than successful output',async()=>{
  api.post.mockRejectedValue({message:'模型超时',response:{data:{status:'failed',session_id:'failed_session',error:{code:'upstream_timeout'}}}});
  render(<ChatInterface/>);fireEvent.change(screen.getByLabelText('选课需求'),{target:{value:'查课程'}});fireEvent.click(screen.getByRole('button',{name:'发送'}));
  await screen.findByText('模型超时');expect(screen.getByRole('alert')).toBeInTheDocument();
});
test('discloses deterministic evidence rendering instead of claiming model-only output',async()=>{
  api.post.mockResolvedValue({session_id:'template',status:'completed',answer:'历史GPA为3.86。',answer_mode:'verified_template',courses:[],evidence:[],effective_constraints:{},query:''});
  render(<ChatInterface/>);fireEvent.change(screen.getByLabelText('选课需求'),{target:{value:'查询GPA'}});fireEvent.click(screen.getByRole('button',{name:'发送'}));
  await screen.findByText('按核验数据整理');expect(screen.getByText('历史GPA为3.86。')).toBeInTheDocument();
});
