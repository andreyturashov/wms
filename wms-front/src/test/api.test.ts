import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// mockFetch needs to be declared before the dynamic import
const mockFetch = vi.fn();

beforeEach(() => {
  mockFetch.mockReset();
  vi.stubGlobal('fetch', mockFetch);
  localStorage.clear();
});

afterEach(() => {
  vi.restoreAllMocks();
});

// Helper to create mock Response objects
function jsonResponse(data: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: new Headers({ 'content-type': 'application/json' }),
    json: () => Promise.resolve(data),
    text: () => Promise.resolve(JSON.stringify(data)),
  } as unknown as Response;
}

function emptyResponse(status = 204): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: new Headers(),
    json: () => Promise.reject(new Error('no body')),
    text: () => Promise.resolve(''),
  } as unknown as Response;
}

describe('API module', () => {
  // Use dynamic imports so mocks are in place
  const getApi = async () => {
    // Reset module registry to pick up fresh mocked fetch
    vi.resetModules();
    return import('../api/index');
  };

  describe('authApi', () => {
    it('register sends POST and stores token', async () => {
      const responseData = {
        access_token: 'tok123',
        token_type: 'bearer',
        user: { id: '1', email: 'a@b.com', username: 'alice' },
      };
      mockFetch.mockResolvedValueOnce(jsonResponse(responseData));

      const { authApi } = await getApi();
      const result = await authApi.register({
        email: 'a@b.com',
        username: 'alice',
        password: 'pass',
      });

      expect(result).toEqual(responseData);
      expect(localStorage.getItem('token')).toBe('tok123');
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/auth/register'),
        expect.objectContaining({ method: 'POST' }),
      );
    });

    it('login sends form-urlencoded POST and stores token', async () => {
      const responseData = {
        access_token: 'tok456',
        token_type: 'bearer',
        user: { id: '1', email: 'a@b.com', username: 'alice' },
      };
      mockFetch.mockResolvedValueOnce(jsonResponse(responseData));

      const { authApi } = await getApi();
      const result = await authApi.login({ email: 'a@b.com', password: 'pass' });

      expect(result).toEqual(responseData);
      expect(localStorage.getItem('token')).toBe('tok456');

      const [, opts] = mockFetch.mock.calls[0];
      expect(opts.headers['Content-Type']).toBe('application/x-www-form-urlencoded');
    });

    it('me sends Authorization header', async () => {
      localStorage.setItem('token', 'mytoken');
      const user = { id: '1', email: 'a@b.com', username: 'alice' };
      mockFetch.mockResolvedValueOnce(jsonResponse(user));

      const { authApi } = await getApi();
      const result = await authApi.me();

      expect(result).toEqual(user);
      const [, opts] = mockFetch.mock.calls[0];
      expect(opts.headers['Authorization']).toBe('Bearer mytoken');
    });

    it('logout removes token from localStorage', async () => {
      localStorage.setItem('token', 'mytoken');
      const { authApi } = await getApi();
      authApi.logout();
      expect(localStorage.getItem('token')).toBeNull();
    });
  });

  describe('tasksApi', () => {
    it('getAll fetches tasks', async () => {
      const tasks = [{ id: '1', title: 'Task 1' }];
      mockFetch.mockResolvedValueOnce(jsonResponse(tasks));

      const { tasksApi } = await getApi();
      const result = await tasksApi.getAll();

      expect(result).toEqual(tasks);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/tasks'),
        expect.any(Object),
      );
    });

    it('create sends POST with body', async () => {
      const newTask = { id: '2', title: 'New Task' };
      mockFetch.mockResolvedValueOnce(jsonResponse(newTask));

      const { tasksApi } = await getApi();
      const result = await tasksApi.create({
        title: 'New Task',
        description: '',
        status: 'todo',
        priority: 'medium',
      });

      expect(result).toEqual(newTask);
      const [, opts] = mockFetch.mock.calls[0];
      expect(opts.method).toBe('POST');
      expect(JSON.parse(opts.body)).toEqual(
        expect.objectContaining({ title: 'New Task' }),
      );
    });

    it('update sends PUT with body', async () => {
      const updated = { id: '1', title: 'Updated' };
      mockFetch.mockResolvedValueOnce(jsonResponse(updated));

      const { tasksApi } = await getApi();
      const result = await tasksApi.update('1', { title: 'Updated' });

      expect(result).toEqual(updated);
      const [url, opts] = mockFetch.mock.calls[0];
      expect(url).toContain('/tasks/1');
      expect(opts.method).toBe('PUT');
    });

    it('delete sends DELETE', async () => {
      mockFetch.mockResolvedValueOnce(emptyResponse());

      const { tasksApi } = await getApi();
      await tasksApi.delete('1');

      const [url, opts] = mockFetch.mock.calls[0];
      expect(url).toContain('/tasks/1');
      expect(opts.method).toBe('DELETE');
    });

    it('updateStatus sends PUT to status endpoint', async () => {
      const task = { id: '1', status: 'done' };
      mockFetch.mockResolvedValueOnce(jsonResponse(task));

      const { tasksApi } = await getApi();
      await tasksApi.updateStatus('1', 'done');

      const [url, opts] = mockFetch.mock.calls[0];
      expect(url).toContain('/tasks/1/status');
      expect(opts.method).toBe('PUT');
      expect(JSON.parse(opts.body)).toEqual({ status: 'done' });
    });
  });

  describe('commentsApi', () => {
    it('getByTaskId fetches comments for a task', async () => {
      const comments = [{ id: 'c1', content: 'Hello' }];
      mockFetch.mockResolvedValueOnce(jsonResponse(comments));

      const { commentsApi } = await getApi();
      const result = await commentsApi.getByTaskId('task-1');

      expect(result).toEqual(comments);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/tasks/task-1/comments'),
        expect.any(Object),
      );
    });

    it('getByAuthor passes user_id query param', async () => {
      mockFetch.mockResolvedValueOnce(jsonResponse([]));

      const { commentsApi } = await getApi();
      await commentsApi.getByAuthor({ user_id: 'u1' });

      const [url] = mockFetch.mock.calls[0];
      expect(url).toContain('user_id=u1');
    });

    it('getByAuthor passes agent_id query param', async () => {
      mockFetch.mockResolvedValueOnce(jsonResponse([]));

      const { commentsApi } = await getApi();
      await commentsApi.getByAuthor({ agent_id: 'a1' });

      const [url] = mockFetch.mock.calls[0];
      expect(url).toContain('agent_id=a1');
    });

    it('create sends POST with body', async () => {
      const comment = { id: 'c2', content: 'New comment' };
      mockFetch.mockResolvedValueOnce(jsonResponse(comment));

      const { commentsApi } = await getApi();
      const result = await commentsApi.create('task-1', {
        content: 'New comment',
        agent_id: null,
        parent_id: null,
      });

      expect(result).toEqual(comment);
      const [url, opts] = mockFetch.mock.calls[0];
      expect(url).toContain('/tasks/task-1/comments');
      expect(opts.method).toBe('POST');
    });

    it('delete sends DELETE', async () => {
      mockFetch.mockResolvedValueOnce(emptyResponse());

      const { commentsApi } = await getApi();
      await commentsApi.delete('task-1', 'c1');

      const [url, opts] = mockFetch.mock.calls[0];
      expect(url).toContain('/tasks/task-1/comments/c1');
      expect(opts.method).toBe('DELETE');
    });
  });

  describe('error handling', () => {
    it('throws ApiError on non-ok response with JSON detail', async () => {
      mockFetch.mockResolvedValueOnce(
        jsonResponse({ detail: 'Not found' }, 404),
      );

      const { tasksApi } = await getApi();
      await expect(tasksApi.getAll()).rejects.toThrow('Not found');
    });

    it('throws ApiError on non-ok response with text body', async () => {
      const resp = {
        ok: false,
        status: 500,
        headers: new Headers({ 'content-type': 'text/plain' }),
        json: () => Promise.reject(new Error('not json')),
        text: () => Promise.resolve('Internal Server Error'),
      } as unknown as Response;
      mockFetch.mockResolvedValueOnce(resp);

      const { tasksApi } = await getApi();
      await expect(tasksApi.getAll()).rejects.toThrow('Internal Server Error');
    });
  });

  describe('agentsApi', () => {
    it('getAll fetches agents with active_only default', async () => {
      mockFetch.mockResolvedValueOnce(jsonResponse([]));

      const { agentsApi } = await getApi();
      await agentsApi.getAll();

      const [url] = mockFetch.mock.calls[0];
      expect(url).toContain('active_only=true');
    });
  });

  describe('usersApi', () => {
    it('getAll fetches all users', async () => {
      const users = [{ id: '1', email: 'a@b.com', username: 'alice' }];
      mockFetch.mockResolvedValueOnce(jsonResponse(users));

      const { usersApi } = await getApi();
      const result = await usersApi.getAll();

      expect(result).toEqual(users);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/auth/users'),
        expect.any(Object),
      );
    });
  });
});
