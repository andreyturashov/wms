import type { Agent, Task, User, Comment } from '../types';

export const mockUser: User = {
  id: 'user-1',
  email: 'alice@example.com',
  username: 'alice',
};

export const mockUser2: User = {
  id: 'user-2',
  email: 'bob@example.com',
  username: 'bob',
};

export const mockAgent: Agent = {
  id: 'agent-1',
  key: 'executor',
  name: 'Executor Agent',
  description: 'Takes tasks as described and produces clear, actionable execution plans.',
  is_active: true,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
};

export const mockAgent2: Agent = {
  id: 'agent-2',
  key: 'thinker',
  name: 'Thinker Agent',
  description: 'Analyses problems and generates creative ideas and alternative approaches.',
  is_active: true,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
};

export const mockTask: Task = {
  id: 'task-1',
  title: 'Fix login bug',
  description: 'Users cannot log in with special characters',
  status: 'todo',
  priority: 'high',
  agent_id: null,
  assigned_agent: null,
  assigned_user_id: null,
  assigned_username: null,
  due_date: '2024-06-15',
  user_id: 'user-1',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
};

export const mockTaskInProgress: Task = {
  id: 'task-2',
  title: 'Add dashboard',
  description: 'Build a new dashboard page',
  status: 'in_progress',
  priority: 'medium',
  agent_id: 'agent-1',
  assigned_agent: 'Executor Agent',
  assigned_user_id: null,
  assigned_username: null,
  due_date: null,
  user_id: 'user-1',
  created_at: '2024-01-02T00:00:00Z',
  updated_at: '2024-01-02T00:00:00Z',
};

export const mockTaskDone: Task = {
  id: 'task-3',
  title: 'Write tests',
  description: '',
  status: 'done',
  priority: 'low',
  agent_id: null,
  assigned_agent: null,
  assigned_user_id: 'user-2',
  assigned_username: 'bob',
  due_date: null,
  user_id: 'user-1',
  created_at: '2024-01-03T00:00:00Z',
  updated_at: '2024-01-03T00:00:00Z',
};

export const mockComment: Comment = {
  id: 'comment-1',
  task_id: 'task-1',
  task_title: 'Fix login bug',
  content: 'This needs urgent attention.',
  user_id: 'user-1',
  agent_id: null,
  author_name: 'alice',
  author_type: 'user',
  parent_id: null,
  replies: [],
  created_at: '2024-01-10T12:00:00Z',
};

export const mockCommentWithReplies: Comment = {
  id: 'comment-2',
  task_id: 'task-1',
  task_title: 'Fix login bug',
  content: 'I am investigating.',
  user_id: null,
  agent_id: 'agent-1',
  author_name: 'Executor Agent',
  author_type: 'agent',
  parent_id: null,
  replies: [
    {
      id: 'comment-3',
      task_id: 'task-1',
      task_title: 'Fix login bug',
      content: 'Thanks for looking into it!',
      user_id: 'user-1',
      agent_id: null,
      author_name: 'alice',
      author_type: 'user',
      parent_id: 'comment-2',
      replies: [],
      created_at: '2024-01-10T13:00:00Z',
    },
  ],
  created_at: '2024-01-10T12:30:00Z',
};

export const allMockTasks: Task[] = [mockTask, mockTaskInProgress, mockTaskDone];
