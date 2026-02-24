import { useEffect, useRef, useState } from 'react';
import type { Agent, Task, User } from '../types';
import { tasksApi } from '../api';

interface TaskCardProps {
  task: Task;
  agents: Agent[];
  users: User[];
  onUpdate: (task: Task) => void;
  onDelete: (id: string) => void;
}

const priorityColors = {
  low: 'bg-green-100 text-green-800',
  medium: 'bg-yellow-100 text-yellow-800',
  high: 'bg-red-100 text-red-800',
};

export function TaskCard({ task, agents, users, onUpdate, onDelete }: TaskCardProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [saving, setSaving] = useState(false);

  // Edit form state
  const [editTitle, setEditTitle] = useState(task.title);
  const [editDescription, setEditDescription] = useState(task.description);
  const [editPriority, setEditPriority] = useState<Task['priority']>(task.priority);
  // Unified assignee: "agent:<id>" | "user:<id>" | ""
  const [editAssignee, setEditAssignee] = useState(() => {
    if (task.agent_id) return `agent:${task.agent_id}`;
    if (task.assigned_user_id) return `user:${task.assigned_user_id}`;
    return '';
  });
  const [editDueDate, setEditDueDate] = useState(task.due_date ?? '');

  const titleInputRef = useRef<HTMLInputElement>(null);

  // Sync form state when task prop changes (e.g. after drag-and-drop status update)
  useEffect(() => {
    if (!isEditing) {
      setEditTitle(task.title);
      setEditDescription(task.description);
      setEditPriority(task.priority);
      if (task.agent_id) setEditAssignee(`agent:${task.agent_id}`);
      else if (task.assigned_user_id) setEditAssignee(`user:${task.assigned_user_id}`);
      else setEditAssignee('');
      setEditDueDate(task.due_date ?? '');
    }
  }, [task, isEditing]);

  // Focus title input when entering edit mode
  useEffect(() => {
    if (isEditing) {
      titleInputRef.current?.focus();
    }
  }, [isEditing]);

  const handleDragStart = (e: React.DragEvent) => {
    if (isEditing) {
      e.preventDefault();
      return;
    }
    e.dataTransfer.setData('taskId', task.id);
    setIsDragging(true);
  };

  const handleDragEnd = () => {
    setIsDragging(false);
  };

  const handleDelete = async () => {
    if (confirm('Are you sure you want to delete this task?')) {
      await tasksApi.delete(task.id);
      onDelete(task.id);
    }
  };

  const startEditing = () => {
    setEditTitle(task.title);
    setEditDescription(task.description);
    setEditPriority(task.priority);
    if (task.agent_id) setEditAssignee(`agent:${task.agent_id}`);
    else if (task.assigned_user_id) setEditAssignee(`user:${task.assigned_user_id}`);
    else setEditAssignee('');
    setEditDueDate(task.due_date ?? '');
    setIsEditing(true);
  };

  const cancelEditing = () => {
    setIsEditing(false);
  };

  const saveEditing = async () => {
    if (!editTitle.trim()) return;
    setSaving(true);
    try {
      // Parse unified assignee value
      let agentId: string | null = null;
      let assignedUserId: string | null = null;
      if (editAssignee.startsWith('agent:')) {
        agentId = editAssignee.slice(6);
      } else if (editAssignee.startsWith('user:')) {
        assignedUserId = editAssignee.slice(5);
      }

      const updatedTask = await tasksApi.update(task.id, {
        title: editTitle.trim(),
        description: editDescription,
        priority: editPriority,
        agent_id: agentId,
        assigned_user_id: assignedUserId,
        due_date: editDueDate || null,
      });
      onUpdate(updatedTask);
      setIsEditing(false);
    } catch (error) {
      console.error('Failed to save task:', error);
    } finally {
      setSaving(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      cancelEditing();
    }
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      void saveEditing();
    }
  };

  const assignedAgent = task.agent_id
    ? agents.find((agent) => agent.id === task.agent_id) ?? null
    : null;

  const assignedUser = task.assigned_user_id
    ? users.find((u) => u.id === task.assigned_user_id) ?? null
    : null;

  // --- Edit mode ---
  if (isEditing) {
    return (
      <div
        className="bg-white rounded-lg shadow-lg ring-2 ring-blue-400 p-3 mb-2"
        onKeyDown={handleKeyDown}
      >
        {/* Title */}
        <input
          ref={titleInputRef}
          type="text"
          value={editTitle}
          onChange={(e) => setEditTitle(e.target.value)}
          placeholder="Task title"
          className="w-full font-semibold text-gray-800 text-sm px-2 py-1 border border-gray-300 rounded-md mb-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />

        {/* Description */}
        <textarea
          value={editDescription}
          onChange={(e) => setEditDescription(e.target.value)}
          placeholder="Description (optional)"
          rows={2}
          className="w-full text-gray-600 text-xs px-2 py-1 border border-gray-300 rounded-md mb-2 resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
        />

        {/* Priority & Due Date row */}
        <div className="grid grid-cols-2 gap-2 mb-2">
          <select
            value={editPriority}
            onChange={(e) => setEditPriority(e.target.value as Task['priority'])}
            className="px-2 py-1 border border-gray-300 rounded-md text-xs focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
          </select>
          <input
            type="date"
            value={editDueDate}
            onChange={(e) => setEditDueDate(e.target.value)}
            className="px-2 py-1 border border-gray-300 rounded-md text-xs focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        {/* Assignee (agents + users) */}
        <select
          value={editAssignee}
          onChange={(e) => setEditAssignee(e.target.value)}
          className="w-full px-2 py-1 border border-gray-300 rounded-md text-xs mb-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">Unassigned</option>
          {users.length > 0 && (
            <optgroup label="Users">
              {users.map((u) => (
                <option key={u.id} value={`user:${u.id}`}>
                  {u.username}
                </option>
              ))}
            </optgroup>
          )}
          {agents.length > 0 && (
            <optgroup label="Agents">
              {agents.map((agent) => (
                <option key={agent.id} value={`agent:${agent.id}`}>
                  {agent.name}
                </option>
              ))}
            </optgroup>
          )}
        </select>

        {/* Actions */}
        <div className="flex justify-end gap-2">
          <button
            onClick={cancelEditing}
            disabled={saving}
            className="px-2 py-1 text-xs text-gray-600 bg-gray-100 rounded-md hover:bg-gray-200 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={() => void saveEditing()}
            disabled={saving || !editTitle.trim()}
            className="px-2 py-1 text-xs text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50"
          >
            {saving ? 'Saving…' : 'Save'}
          </button>
        </div>
        <p className="text-[10px] text-gray-400 mt-1 text-right">⌘+Enter to save · Esc to cancel</p>
      </div>
    );
  }

  // --- View mode ---
  return (
    <div
      draggable
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
      onDoubleClick={startEditing}
      className={`bg-white rounded-lg shadow-md p-3 mb-2 cursor-move hover:shadow-lg transition-shadow ${
        isDragging ? 'opacity-50' : ''
      }`}
    >
      <div className="flex justify-between items-start mb-2">
        <h3 className="font-semibold text-gray-800 text-sm">{task.title}</h3>
        <div className="flex gap-1">
          <button
            onClick={startEditing}
            className="text-gray-400 hover:text-blue-500 text-xs"
            title="Edit task"
          >
            ✎
          </button>
          <button
            onClick={handleDelete}
            className="text-gray-400 hover:text-red-500 text-xs"
            title="Delete task"
          >
            ✕
          </button>
        </div>
      </div>
      {task.description && (
        <p className="text-gray-600 text-xs mb-2 line-clamp-2">{task.description}</p>
      )}
      {assignedAgent && (
        <div className="mb-2">
          <span className="text-xs px-2 py-1 rounded-full bg-indigo-100 text-indigo-800">
            🤖 {assignedAgent.name}
          </span>
        </div>
      )}
      {assignedUser && (
        <div className="mb-2">
          <span className="text-xs px-2 py-1 rounded-full bg-emerald-100 text-emerald-800">
            👤 {assignedUser.username}
          </span>
        </div>
      )}
      <div className="flex justify-between items-center">
        <span
          className={`text-xs px-2 py-1 rounded-full ${priorityColors[task.priority]}`}
        >
          {task.priority}
        </span>
        {task.due_date && (
          <span className="text-xs text-gray-500">
            {new Date(task.due_date).toLocaleDateString()}
          </span>
        )}
      </div>
    </div>
  );
}
