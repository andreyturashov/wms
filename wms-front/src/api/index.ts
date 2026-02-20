// Real API - connects to FastAPI backend

import type { Task, CreateTaskRequest, UpdateTaskRequest, AuthResponse, LoginRequest, RegisterRequest, User } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

const getHeaders = (): HeadersInit => {
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };
  
  const token = localStorage.getItem('token');
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  return headers;
};

const handleResponse = async <T>(response: Response): Promise<T> => {
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'An error occurred' }));
    throw new ApiError(response.status, error.detail || 'An error occurred');
  }
  return response.json();
};

// Auth API
export const authApi = {
  register: async (data: RegisterRequest): Promise<AuthResponse> => {
    const response = await fetch(`${API_BASE_URL}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return handleResponse<AuthResponse>(response);
  },

  login: async (data: LoginRequest): Promise<AuthResponse> => {
    const params = new URLSearchParams();
    params.append('username', data.email);
    params.append('password', data.password);
    
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: params,
    });
    const result = await handleResponse<AuthResponse>(response);
    localStorage.setItem('token', result.access_token);
    return result;
  },

  me: async (): Promise<User> => {
    const response = await fetch(`${API_BASE_URL}/auth/me`, {
      headers: getHeaders(),
    });
    return handleResponse<User>(response);
  },

  logout: () => {
    localStorage.removeItem('token');
  },
};

// Tasks API
export const tasksApi = {
  getAll: async (): Promise<Task[]> => {
    const response = await fetch(`${API_BASE_URL}/tasks`, {
      headers: getHeaders(),
    });
    return handleResponse<Task[]>(response);
  },

  getById: async (id: string): Promise<Task> => {
    const response = await fetch(`${API_BASE_URL}/tasks/${id}`, {
      headers: getHeaders(),
    });
    return handleResponse<Task>(response);
  },

  create: async (data: CreateTaskRequest): Promise<Task> => {
    const response = await fetch(`${API_BASE_URL}/tasks`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify(data),
    });
    return handleResponse<Task>(response);
  },

  update: async (id: string, data: UpdateTaskRequest): Promise<Task> => {
    const response = await fetch(`${API_BASE_URL}/tasks/${id}`, {
      method: 'PUT',
      headers: getHeaders(),
      body: JSON.stringify(data),
    });
    return handleResponse<Task>(response);
  },

  delete: async (id: string): Promise<void> => {
    const response = await fetch(`${API_BASE_URL}/tasks/${id}`, {
      method: 'DELETE',
      headers: getHeaders(),
    });
    if (!response.ok) {
      throw new ApiError(response.status, 'Failed to delete task');
    }
  },

  updateStatus: async (id: string, status: Task['status']): Promise<Task> => {
    const response = await fetch(`${API_BASE_URL}/tasks/${id}/status`, {
      method: 'PUT',
      headers: getHeaders(),
      body: JSON.stringify({ status }),
    });
    return handleResponse<Task>(response);
  },
};
