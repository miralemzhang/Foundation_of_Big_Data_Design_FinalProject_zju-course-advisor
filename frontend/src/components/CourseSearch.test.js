import React from 'react';
import {render,screen,fireEvent,waitFor} from '@testing-library/react';
import CourseSearch from './CourseSearch';
import api from '../api/client';
jest.mock('../api/client',()=>({post:jest.fn()}));
jest.mock('../state/AppContext',()=>({useApp:()=>({meta:{categories:['当代社会'],colleges:[]}})}));
jest.mock('./CourseCard',()=>({course})=><div>{course.course_name}</div>);
beforeEach(()=>jest.clearAllMocks());
test('applies a numeric hard filter and renders empty result without a fake recommendation',async()=>{
  api.post.mockResolvedValue({results:[],total:0});render(<CourseSearch/>);
  await waitFor(()=>expect(api.post).toHaveBeenCalledTimes(1));
  await waitFor(()=>expect(screen.getByRole('button',{name:'筛选课程'})).not.toHaveClass('ant-btn-loading'));
  fireEvent.change(screen.getByLabelText('历史GPA下限'),{target:{value:'4.3'}});fireEvent.blur(screen.getByLabelText('历史GPA下限'));
  fireEvent.click(screen.getByRole('button',{name:'筛选课程'}));
  await waitFor(()=>expect(api.post).toHaveBeenLastCalledWith('/search',expect.objectContaining({filters:{min_gpa:4.3},page:1})));
  expect(await screen.findByText('没有符合条件的课程，可自行修改筛选条件')).toBeInTheDocument();
});
