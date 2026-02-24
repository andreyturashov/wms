import type { Agent, User } from '../types';
import type { AuthorSelection } from './CommentPanel';

interface SidebarProps {
  users: User[];
  agents: Agent[];
  selection: AuthorSelection;
  onSelect: (selection: AuthorSelection) => void;
}

export function Sidebar({ users, agents, selection, onSelect }: SidebarProps) {
  const handleClick = (type: 'user' | 'agent', id: string, name: string) => {
    if (selection?.type === type && selection.id === id) {
      onSelect(null); // toggle off
    } else {
      onSelect({ type, id, name });
    }
  };

  return (
    <aside className="w-56 flex-shrink-0 bg-white rounded-lg shadow-md overflow-hidden flex flex-col max-h-[calc(100vh-8rem)]">
      {/* Users section */}
      <div className="p-3 border-b border-gray-200">
        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
          Users
        </h3>
        <div className="space-y-1">
          {users.map((u) => (
            <button
              key={u.id}
              onClick={() => handleClick('user', u.id, u.username)}
              className={`w-full text-left px-2 py-1.5 rounded-md text-sm flex items-center gap-2 transition-colors ${
                selection?.type === 'user' && selection.id === u.id
                  ? 'bg-emerald-100 text-emerald-800 font-medium'
                  : 'text-gray-700 hover:bg-gray-100'
              }`}
            >
              <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-emerald-100 text-emerald-700 text-xs flex-shrink-0">
                👤
              </span>
              <span className="truncate">{u.username}</span>
            </button>
          ))}
          {users.length === 0 && (
            <p className="text-xs text-gray-400 italic px-2">No users</p>
          )}
        </div>
      </div>

      {/* Agents section */}
      <div className="p-3">
        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
          Agents
        </h3>
        <div className="space-y-1">
          {agents.map((a) => (
            <button
              key={a.id}
              onClick={() => handleClick('agent', a.id, a.name)}
              className={`w-full text-left px-2 py-1.5 rounded-md text-sm flex items-center gap-2 transition-colors ${
                selection?.type === 'agent' && selection.id === a.id
                  ? 'bg-indigo-100 text-indigo-800 font-medium'
                  : 'text-gray-700 hover:bg-gray-100'
              }`}
            >
              <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-indigo-100 text-indigo-700 text-xs flex-shrink-0">
                🤖
              </span>
              <span className="truncate">{a.name}</span>
            </button>
          ))}
          {agents.length === 0 && (
            <p className="text-xs text-gray-400 italic px-2">No agents</p>
          )}
        </div>
      </div>
    </aside>
  );
}
