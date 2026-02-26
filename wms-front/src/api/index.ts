// Real API - connects to FastAPI backend

import type { Task, CreateTaskRequest, UpdateTaskRequest, AuthResponse, LoginRequest, RegisterRequest, User, Agent, Comment, CreateCommentRequest } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
const TOKEN_STORAGE_KEY = 'token';

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

  const token = localStorage.getItem(TOKEN_STORAGE_KEY);
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  return headers;
};

const getErrorMessage = async (response: Response): Promise<string> => {
  const contentType = response.headers.get('content-type') || '';

  if (contentType.includes('application/json')) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    if (payload?.detail) {
      return payload.detail;
    }
  }

  const text = await response.text().catch(() => '');
  return text || 'An error occurred';
};

const handleResponse = async <T>(response: Response): Promise<T> => {
  if (!response.ok) {
    throw new ApiError(response.status, await getErrorMessage(response));
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
};

const request = async <T>(url: string, options: RequestInit = {}): Promise<T> => {
  const response = await fetch(url, options);
  return handleResponse<T>(response);
};

// Auth API
export const authApi = {
  register: async (data: RegisterRequest): Promise<AuthResponse> => {
    const result = await request<AuthResponse>(`${API_BASE_URL}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    localStorage.setItem(TOKEN_STORAGE_KEY, result.access_token);
    return result;
  },

  login: async (data: LoginRequest): Promise<AuthResponse> => {
    const params = new URLSearchParams();
    params.append('username', data.email);
    params.append('password', data.password);

    const result = await request<AuthResponse>(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: params,
    });
    localStorage.setItem(TOKEN_STORAGE_KEY, result.access_token);
    return result;
  },

  me: async (): Promise<User> => {
    return request<User>(`${API_BASE_URL}/auth/me`, {
      headers: getHeaders(),
    });
  },

  logout: () => {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
  },
};

// Tasks API
export const tasksApi = {
  getAll: async (): Promise<Task[]> => {
    return request<Task[]>(`${API_BASE_URL}/tasks`, {
      headers: getHeaders(),
    });
  },

  getById: async (id: string): Promise<Task> => {
    return request<Task>(`${API_BASE_URL}/tasks/${id}`, {
      headers: getHeaders(),
    });
  },

  create: async (data: CreateTaskRequest): Promise<Task> => {
    return request<Task>(`${API_BASE_URL}/tasks`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify(data),
    });
  },

  update: async (id: string, data: UpdateTaskRequest): Promise<Task> => {
    return request<Task>(`${API_BASE_URL}/tasks/${id}`, {
      method: 'PUT',
      headers: getHeaders(),
      body: JSON.stringify(data),
    });
  },

  delete: async (id: string): Promise<void> => {
    await request<void>(`${API_BASE_URL}/tasks/${id}`, {
      method: 'DELETE',
      headers: getHeaders(),
    });
  },

  updateStatus: async (id: string, status: Task['status']): Promise<Task> => {
    return request<Task>(`${API_BASE_URL}/tasks/${id}/status`, {
      method: 'PUT',
      headers: getHeaders(),
      body: JSON.stringify({ status }),
    });
  },
};

export const agentsApi = {
  getAll: async (activeOnly = true): Promise<Agent[]> => {
    return request<Agent[]>(`${API_BASE_URL}/agents?active_only=${activeOnly}`, {
      headers: getHeaders(),
    });
  },
};

export const usersApi = {
  getAll: async (): Promise<User[]> => {
    return request<User[]>(`${API_BASE_URL}/auth/users`, {
      headers: getHeaders(),
    });
  },
};

export const commentsApi = {
  getByTaskId: async (taskId: string): Promise<Comment[]> => {
    return request<Comment[]>(`${API_BASE_URL}/tasks/${taskId}/comments`, {
      headers: getHeaders(),
    });
  },

  getByAuthor: async (params: { user_id?: string; agent_id?: string }): Promise<Comment[]> => {
    const qs = new URLSearchParams();
    if (params.user_id) qs.set('user_id', params.user_id);
    if (params.agent_id) qs.set('agent_id', params.agent_id);
    return request<Comment[]>(`${API_BASE_URL}/comments?${qs.toString()}`, {
      headers: getHeaders(),
    });
  },

  create: async (taskId: string, data: CreateCommentRequest): Promise<Comment> => {
    return request<Comment>(`${API_BASE_URL}/tasks/${taskId}/comments`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify(data),
    });
  },

  delete: async (taskId: string, commentId: string): Promise<void> => {
    await request<void>(`${API_BASE_URL}/tasks/${taskId}/comments/${commentId}`, {
      method: 'DELETE',
      headers: getHeaders(),
    });
  },
};
