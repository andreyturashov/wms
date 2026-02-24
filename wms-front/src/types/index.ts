export interface Agent {
  id: string;
  key: string;
  name: string;
  description: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Task {
  id: string;
  title: string;
  description: string;
  status: 'todo' | 'in_progress' | 'done';
  priority: 'low' | 'medium' | 'high';
  agent_id: string | null;
  assigned_agent: string | null;
  assigned_user_id: string | null;
  assigned_username: string | null;
  due_date: string | null;
  user_id: string;
  created_at: string;
  updated_at: string;
}

export interface CreateTaskRequest {
  title: string;
  description: string;
  status: 'todo' | 'in_progress' | 'done';
  priority: 'low' | 'medium' | 'high';
  agent_id?: string | null;
  assigned_agent?: string | null;
  assigned_user_id?: string | null;
  due_date?: string | null;
}

export interface UpdateTaskRequest {
  title?: string;
  description?: string;
  status?: 'todo' | 'in_progress' | 'done';
  priority?: 'low' | 'medium' | 'high';
  agent_id?: string | null;
  assigned_agent?: string | null;
  assigned_user_id?: string | null;
  due_date?: string | null;
}

export interface User {
  id: string;
  email: string;
  username: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  username: string;
  password: string;
}
