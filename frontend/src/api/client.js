import axios from 'axios';
import { userId } from '../utils/storage';
const api = axios.create({ baseURL: '/api', timeout: 130000 });
api.interceptors.request.use(config => {
  config.headers['X-User-ID'] = userId();
  return config;
});
api.interceptors.response.use(response => response.data, error => {
  error.message = error.response?.data?.error?.message || error.response?.data?.answer ||
    (error.code === 'ECONNABORTED' ? '请求超时，请稍后重试' : '暂时无法连接服务，请检查后端是否启动');
  return Promise.reject(error);
});
export default api;
