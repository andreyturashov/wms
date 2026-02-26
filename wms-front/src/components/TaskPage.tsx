import { useCallback, useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import type { Agent, Task, User } from '../types';
import { tasksApi, agentsApi, usersApi, authApi } from '../api';
import { CommentSection } from './CommentSection';

const priorityColors = {
  low: 'bg-green-100 text-green-800',
  medium: 'bg-yellow-100 text-yellow-800',
  high: 'bg-red-100 text-red-800',
};

const statusLabels: Record<Task['status'], string> = {
  todo: 'To Do',
  in_progress: 'In Progress',
  done: 'Done',
};

const statusColors: Record<Task['status'], string> = {
  todo: 'bg-gray-100 text-gray-800',
  in_progress: 'bg-blue-100 text-blue-800',
  done: 'bg-green-100 text-green-800',
};

export function TaskPage() {
  const { taskId } = useParams<{ taskId: string }>();
  const [task, setTask] = useState<Task | null>(null);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    if (!taskId) return;
    setLoading(true);
    setError(null);
    try {
      const [taskData, agentsData, usersData, me] = await Promise.all([
        tasksApi.getById(taskId),
        agentsApi.getAll(true),
        usersApi.getAll(),
        authApi.me(),
      ]);
      setTask(taskData);
      setAgents(agentsData);
      setUsers(usersData);
      setCurrentUser(me);
    } catch {
      setError('Task not found or you are not authorized.');
    } finally {
      setLoading(false);
    }
  }, [taskId]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <p className="text-gray-500">Loading task…</p>
      </div>
    );
  }

  if (error || !task) {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center gap-4">
        <p className="text-red-600">{error ?? 'Task not found'}</p>
        <Link to="/" className="text-blue-600 hover:underline">
          ← Back to Board
        </Link>
      </div>
    );
  }

  const assignedAgent = task.agent_id
    ? agents.find((a) => a.id === task.agent_id) ?? null
    : null;

  const assignedUser = task.assigned_user_id
    ? users.find((u) => u.id === task.assigned_user_id) ?? null
    : null;

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm">
        <div className="max-w-3xl mx-auto px-4 py-4 flex items-center gap-3">
          <Link
            to="/"
            className="text-blue-600 hover:text-blue-800 text-sm"
            title="Back to Board"
          >
            ← Board
          </Link>
          <span className="text-gray-300">|</span>
          <h1 className="text-lg font-bold text-gray-800 truncate">{task.title}</h1>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-6">
        {/* Status & Priority */}
        <div className="flex items-center gap-3 mb-4">
          <span className={`text-xs font-medium px-3 py-1 rounded-full ${statusColors[task.status]}`}>
            {statusLabels[task.status]}
          </span>
          <span className={`text-xs font-medium px-3 py-1 rounded-full ${priorityColors[task.priority]}`}>
            {task.priority} priority
          </span>
        </div>

        {/* Description */}
        <div className="bg-white rounded-lg shadow-sm p-5 mb-4">
          <h2 className="text-sm font-semibold text-gray-700 mb-2">Description</h2>
          {task.description ? (
            <p className="text-gray-600 text-sm whitespace-pre-wrap">{task.description}</p>
          ) : (
            <p className="text-gray-400 text-sm italic">No description</p>
          )}
        </div>

        {/* Details */}
        <div className="bg-white rounded-lg shadow-sm p-5 mb-4">
          <h2 className="text-sm font-semibold text-gray-700 mb-3">Details</h2>
          <dl className="grid grid-cols-2 gap-y-2 gap-x-4 text-sm">
            <dt className="text-gray-500">Assignee</dt>
            <dd className="text-gray-800">
              {assignedAgent ? (
                <span className="inline-flex items-center gap-1">
                  🤖 {assignedAgent.name}
                </span>
              ) : assignedUser ? (
                <span className="inline-flex items-center gap-1">
                  👤 {assignedUser.username}
                </span>
              ) : (
                <span className="text-gray-400">Unassigned</span>
              )}
            </dd>

            <dt className="text-gray-500">Due Date</dt>
            <dd className="text-gray-800">
              {task.due_date ? new Date(task.due_date).toLocaleDateString() : (
                <span className="text-gray-400">None</span>
              )}
            </dd>

            <dt className="text-gray-500">Created</dt>
            <dd className="text-gray-800">
              {new Date(task.created_at).toLocaleString()}
            </dd>

            <dt className="text-gray-500">Updated</dt>
            <dd className="text-gray-800">
              {new Date(task.updated_at).toLocaleString()}
            </dd>
          </dl>
        </div>

        {/* Comments */}
        <div className="bg-white rounded-lg shadow-sm p-5">
          <h2 className="text-sm font-semibold text-gray-700 mb-2">Comments</h2>
          {currentUser && (
            <CommentSection
              taskId={task.id}
              agents={agents}
              users={users}
              currentUser={currentUser}
            />
          )}
        </div>
      </main>
    </div>
  );
}
