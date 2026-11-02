import React from 'react';
import {render,screen,fireEvent,waitFor} from '@testing-library/react';
import {AppProvider,useApp} from './AppContext';
import api from '../api/client';
jest.mock('../api/client',()=>({get:jest.fn(),put:jest.fn(),post:jest.fn()}));
function Consumer(){const a=useApp();return <><span>数量{a.shortlist.items.length}</span><button onClick={()=>a.add({offering_id:'o_test'})}>添加</button><button onClick={()=>a.saveShortlist([])}>清空</button></>;}
beforeEach(()=>{localStorage.clear();jest.clearAllMocks();api.get.mockImplementation(path=>Promise.resolve(path==='/meta'?{categories:[]}:{items:[],courses:[],revision:0}));api.post.mockResolvedValue({});});
test('persists shortlist with revisions and avoids duplicate course IDs',async()=>{
  api.put.mockResolvedValue({items:['o_test'],courses:[],revision:1});render(<AppProvider><Consumer/></AppProvider>);
  await waitFor(()=>expect(api.get).toHaveBeenCalledTimes(2));fireEvent.click(screen.getByText('添加'));
  await screen.findByText('数量1');expect(api.put).toHaveBeenCalledWith('/shortlist',{items:['o_test'],revision:0});
  fireEvent.click(screen.getByText('添加'));expect(api.put).toHaveBeenCalledTimes(1);
});
