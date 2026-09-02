import axios from 'axios';
import { supabase } from './supabaseClient';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';
console.log("API_URL is:", API_URL);

const api = axios.create({
  baseURL: API_URL,
});

api.interceptors.request.use(async (config) => {
  const { data: { session } } = await supabase.auth.getSession();
  if (session?.access_token) {
    config.headers.Authorization = `Bearer ${session.access_token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && typeof window !== 'undefined') {
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const getSupervisors = () => api.get('/supervisors/').then(res => res.data.data);
export const createSupervisor = (data: any) => api.post('/supervisors/', data).then(res => res.data.data);

export const getRuns = () => api.get('/runs/').then(res => res.data.data);
export const getRun = (id: string) => api.get(`/runs/${id}`).then(res => res.data.data);
export const getRunActivities = (id: string) => api.get(`/runs/${id}/activities`).then(res => res.data.data);

export const createRun = (data: any) => api.post('/runs/', data).then(res => res.data.data);
export const injectEvent = (runId: string, payload: any) => api.post(`/runs/${runId}/events`, { type: 'event', payload }).then(res => res.data.data);
export const injectInstruction = (runId: string, text: string) => api.post(`/runs/${runId}/instructions`, { type: 'instruction', payload: { instruction: text } }).then(res => res.data.data);

export const terminateRun = (runId: string) => api.post(`/runs/${runId}/terminate`).then(res => res.data.data);
export const pauseRun = (runId: string) => api.post(`/runs/${runId}/pause`).then(res => res.data.data);
export const resumeRun = (runId: string) => api.post(`/runs/${runId}/resume`).then(res => res.data.data);

export default api;
