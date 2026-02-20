import type { Task } from '../types';
import { TaskCard } from './TaskCard';

interface ColumnProps {
  title: string;
  status: Task['status'];
  tasks: Task[];
  onUpdateTask: (task: Task) => void;
  onDeleteTask: (id: string) => void;
  onDrop: (taskId: string, newStatus: Task['status']) => void;
}

const columnColors: Record<Task['status'], string> = {
  todo: 'bg-gray-100',
  in_progress: 'bg-blue-100',
  done: 'bg-green-100',
};

export function Column({ title, status, tasks, onUpdateTask, onDeleteTask, onDrop }: ColumnProps) {
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const taskId = e.dataTransfer.getData('taskId');
    if (taskId) {
      onDrop(taskId, status);
    }
  };

  return (
    <div
      className={`flex-1 min-w-[280px] max-w-[350px] rounded-lg ${columnColors[status]} p-3`}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
    >
      <h2 className="font-bold text-gray-700 mb-3 flex items-center justify-between">
        {title}
        <span className="bg-white text-gray-600 px-2 py-0.5 rounded-full text-sm">
          {tasks.length}
        </span>
      </h2>
      <div className="space-y-2 min-h-[200px]">
        {tasks.map((task) => (
          <TaskCard
            key={task.id}
            task={task}
            onUpdate={onUpdateTask}
            onDelete={onDeleteTask}
          />
        ))}
      </div>
    </div>
  );
}
