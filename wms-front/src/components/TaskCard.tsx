import { useState } from 'react';
import type { Agent, Task } from '../types';
import { tasksApi } from '../api';

interface TaskCardProps {
  task: Task;
  agents: Agent[];
  onUpdate: (task: Task) => void;
  onDelete: (id: string) => void;
}

const priorityColors = {
  low: 'bg-green-100 text-green-800',
  medium: 'bg-yellow-100 text-yellow-800',
  high: 'bg-red-100 text-red-800',
};

export function TaskCard({ task, agents, onUpdate, onDelete }: TaskCardProps) {
  const [isDragging, setIsDragging] = useState(false);

  const handleDragStart = (e: React.DragEvent) => {
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

  const handleAgentChange = async (value: string) => {
    const agentId = (value || null) as Task['agent_id'];
    const updatedTask = await tasksApi.update(task.id, {
      agent_id: agentId,
    });
    onUpdate(updatedTask);
  };

  const assignedAgent = task.agent_id
    ? agents.find((agent) => agent.id === task.agent_id) ?? null
    : null;

  return (
    <div
      draggable
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
      className={`bg-white rounded-lg shadow-md p-3 mb-2 cursor-move hover:shadow-lg transition-shadow ${
        isDragging ? 'opacity-50' : ''
      }`}
    >
      <div className="flex justify-between items-start mb-2">
        <h3 className="font-semibold text-gray-800 text-sm">{task.title}</h3>
        <button
          onClick={handleDelete}
          className="text-gray-400 hover:text-red-500 text-xs"
        >
          ✕
        </button>
      </div>
      {task.description && (
        <p className="text-gray-600 text-xs mb-2 line-clamp-2">{task.description}</p>
      )}
      {assignedAgent && (
        <div className="mb-2">
          <span className="text-xs px-2 py-1 rounded-full bg-indigo-100 text-indigo-800">
            {assignedAgent.name}
          </span>
        </div>
      )}
      <div className="mb-2">
        <select
          value={task.agent_id ?? ''}
          onChange={(e) => void handleAgentChange(e.target.value)}
          className="w-full px-2 py-1 border border-gray-300 rounded-md text-xs focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">Unassigned</option>
          {agents.map((agent) => (
            <option key={agent.id} value={agent.id}>
              {agent.name}
            </option>
          ))}
        </select>
      </div>
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
