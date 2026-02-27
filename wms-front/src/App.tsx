import { useCallback, useEffect, useState } from 'react';
import { Routes, Route } from 'react-router-dom';
import { Column, TaskModal, Sidebar, CommentPanel, TaskPage } from './components';
import type { AuthorSelection } from './components';
import { tasksApi, authApi, agentsApi, usersApi } from './api';
import type { Task, CreateTaskRequest, LoginRequest, RegisterRequest, Agent, User } from './types';

function App() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingTask, setEditingTask] = useState<Task | null>(null);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [isLogin, setIsLogin] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [authorSelection, setAuthorSelection] = useState<AuthorSelection>(null);

  const loadTasks = useCallback(async () => {
    const data = await tasksApi.getAll();
    setTasks(data);
  }, []);

  const loadAgents = useCallback(async () => {
    const data = await agentsApi.getAll(true);
    setAgents(data);
  }, []);

  const loadUsers = useCallback(async () => {
    const data = await usersApi.getAll();
    setUsers(data);
  }, []);

  useEffect(() => {
    const initialize = async () => {
      const token = localStorage.getItem('token');
      if (!token) {
        setLoading(false);
        return;
      }

      try {
        const me = await authApi.me();
        setCurrentUser(me);
        setIsAuthenticated(true);
        await Promise.all([loadTasks(), loadAgents(), loadUsers()]);
      } catch {
        authApi.logout();
        setIsAuthenticated(false);
      } finally {
        setLoading(false);
      }
    };

    void initialize();
  }, [loadTasks, loadAgents, loadUsers]);

  const handleCreateTask = async (data: CreateTaskRequest) => {
    setErrorMessage(null);
    try {
      const newTask = await tasksApi.create(data);
      setTasks((prev) => [...prev, newTask]);
    } catch (error) {
      console.error('Failed to create task:', error);
      setErrorMessage('Failed to create task. Please try again.');
    }
  };

  const handleUpdateTask = (updatedTask: Task) => {
    setTasks((prev) => prev.map((item) => (item.id === updatedTask.id ? updatedTask : item)));
  };

  const handleDeleteTask = (id: string) => {
    setTasks((prev) => prev.filter((task) => task.id !== id));
  };

  const handleStatusChange = async (taskId: string, newStatus: Task['status']) => {
    setErrorMessage(null);
    try {
      const updated = await tasksApi.updateStatus(taskId, newStatus);
      setTasks((prev) => prev.map((task) => (task.id === taskId ? updated : task)));
    } catch (error) {
      console.error('Failed to update task status:', error);
      setErrorMessage('Failed to update task status. Please try again.');
    }
  };

  const handleAuth = async (data: LoginRequest | RegisterRequest, isSignInMode: boolean) => {
    setErrorMessage(null);
    try {
      if (isSignInMode) {
        await authApi.login(data as LoginRequest);
      } else {
        await authApi.register(data as RegisterRequest);
      }

      setIsAuthenticated(true);
      setIsAuthModalOpen(false);
      const me = await authApi.me();
      setCurrentUser(me);
      await Promise.all([loadTasks(), loadAgents(), loadUsers()]);
    } catch (error) {
      console.error('Auth failed:', error);
      setErrorMessage('Authentication failed. Please check your credentials.');
    }
  };

  const handleLogout = () => {
    authApi.logout();
    setIsAuthenticated(false);
    setTasks([]);
    setAgents([]);
    setUsers([]);
    setCurrentUser(null);
    setErrorMessage(null);
    setIsAuthModalOpen(false);
    setIsModalOpen(false);
    setEditingTask(null);
  };

  const todoTasks = tasks.filter((t) => t.status === 'todo');
  const inProgressTasks = tasks.filter((t) => t.status === 'in_progress');
  const doneTasks = tasks.filter((t) => t.status === 'done');

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-xl text-gray-600">Loading...</div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="bg-white p-8 rounded-lg shadow-md w-full max-w-md">
          <h1 className="text-2xl font-bold mb-6 text-center">WMS Task Manager</h1>
          <p className="text-gray-600 mb-6 text-center">Sign in to manage your tasks</p>
          {errorMessage && (
            <p className="mb-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{errorMessage}</p>
          )}
          <button
            onClick={() => setIsAuthModalOpen(true)}
            className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700"
          >
            Sign In / Register
          </button>
        </div>
        {isAuthModalOpen && (
          <AuthModal
            isLogin={isLogin}
            onSubmit={(data) => handleAuth(data, isLogin)}
            onSwitch={() => setIsLogin(!isLogin)}
            onClose={() => setIsAuthModalOpen(false)}
          />
        )}
      </div>
    );
  }

  return (
    <Routes>
      <Route path="/tasks/:taskId" element={<TaskPage />} />
      <Route
        path="*"
        element={
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm">
        <div className="max-w-screen-2xl mx-auto px-4 py-4 flex justify-between items-center">
          <h1 className="text-2xl font-bold text-gray-800">WMS Task Manager</h1>
          <div className="flex gap-3">
            <button
              onClick={() => {
                setEditingTask(null);
                setIsModalOpen(true);
              }}
              className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700"
            >
              + New Task
            </button>
            <button
              onClick={handleLogout}
              className="bg-gray-200 text-gray-700 px-4 py-2 rounded-md hover:bg-gray-300"
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-screen-2xl mx-auto px-4 py-6">
        {errorMessage && (
          <p className="mb-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{errorMessage}</p>
        )}
        {/* Breadcrumb */}
        <nav className="flex items-center gap-1 text-sm mb-4">
          <button
            onClick={() => setAuthorSelection(null)}
            className={`px-2 py-1 rounded-md transition-colors ${
              !authorSelection
                ? 'text-gray-800 font-semibold'
                : 'text-blue-600 hover:text-blue-800 hover:underline'
            }`}
          >
            Board
          </button>
          {authorSelection && (
            <>
              <span className="text-gray-400">/</span>
              <span className="text-gray-800 font-semibold px-2 py-1">
                {authorSelection.type === 'agent' ? '🤖' : '👤'} {authorSelection.name}
              </span>
            </>
          )}
        </nav>
        <div className="flex gap-4">
          <Sidebar users={users} agents={agents} selection={authorSelection} onSelect={setAuthorSelection} />
          {authorSelection ? (
            <CommentPanel selection={authorSelection} agents={agents} users={users} currentUser={currentUser} onTaskCreated={(task) => setTasks((prev) => [...prev, task])} />
          ) : (
            <div className="flex-1 flex gap-4 overflow-x-auto pb-4">
            <Column
              title="To Do"
              status="todo"
              tasks={todoTasks}
              agents={agents}
              users={users}
              currentUser={currentUser}
              onUpdateTask={handleUpdateTask}
              onDeleteTask={handleDeleteTask}
              onDrop={handleStatusChange}
            />
            <Column
              title="In Progress"
              status="in_progress"
              tasks={inProgressTasks}
              agents={agents}
              users={users}
              currentUser={currentUser}
              onUpdateTask={handleUpdateTask}
              onDeleteTask={handleDeleteTask}
              onDrop={handleStatusChange}
            />
            <Column
              title="Done"
              status="done"
              tasks={doneTasks}
              agents={agents}
              users={users}
              currentUser={currentUser}
              onUpdateTask={handleUpdateTask}
              onDeleteTask={handleDeleteTask}
              onDrop={handleStatusChange}
            />
            </div>
          )}
        </div>
      </main>

      <TaskModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSubmit={handleCreateTask}
        task={editingTask}
        agents={agents}
        users={users}
      />
    </div>
        }
      />
    </Routes>
  );
}

function AuthModal({
  isLogin,
  onSubmit,
  onSwitch,
  onClose,
}: {
  isLogin: boolean;
  onSubmit: (data: LoginRequest | RegisterRequest) => Promise<void>;
  onSwitch: () => void;
  onClose: () => void;
}) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [username, setUsername] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isLogin) {
      await onSubmit({ email, password });
    } else {
      await onSubmit({ email, password, username });
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-md">
        <h2 className="text-xl font-bold mb-4">{isLogin ? 'Sign In' : 'Register'}</h2>
        <form onSubmit={handleSubmit}>
          {!isLogin && (
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">Username</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required={!isLogin}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          )}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div className="flex justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 text-white bg-blue-600 rounded-md hover:bg-blue-700"
            >
              {isLogin ? 'Sign In' : 'Register'}
            </button>
          </div>
        </form>
        <p className="mt-4 text-center text-sm text-gray-600">
          {isLogin ? "Don't have an account? " : 'Already have an account? '}
          <button onClick={onSwitch} className="text-blue-600 hover:underline">
            {isLogin ? 'Register' : 'Sign In'}
          </button>
        </p>
      </div>
    </div>
  );
}

export default App;
