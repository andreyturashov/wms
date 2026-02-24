import { useEffect, useState } from 'react';
import type { Comment } from '../types';
import { commentsApi } from '../api';

export type AuthorSelection =
  | { type: 'user'; id: string; name: string }
  | { type: 'agent'; id: string; name: string }
  | null;

interface CommentPanelProps {
  selection: AuthorSelection;
}

export function CommentPanel({ selection }: CommentPanelProps) {
  const [comments, setComments] = useState<Comment[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!selection) {
      setComments([]);
      return;
    }

    const load = async () => {
      setLoading(true);
      try {
        const params =
          selection.type === 'user'
            ? { user_id: selection.id }
            : { agent_id: selection.id };
        const data = await commentsApi.getByAuthor(params);
        setComments(data);
      } catch (err) {
        console.error('Failed to load comments:', err);
        setComments([]);
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, [selection]);

  const formatTime = (iso: string) => {
    const d = new Date(iso);
    return d.toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (!selection) {
    return null;
  }

  return (
    <div className="flex-1 bg-white rounded-lg shadow-md overflow-hidden flex flex-col max-h-[calc(100vh-8rem)]">
      <div className="p-3 border-b border-gray-200">
        <h3 className="text-sm font-semibold text-gray-700">
          {selection.type === 'agent' ? '🤖' : '👤'} Comments by {selection.name}
        </h3>
      </div>

      <div className="flex-1 overflow-y-auto p-3">
        {loading ? (
          <p className="text-xs text-gray-400">Loading…</p>
        ) : comments.length === 0 ? (
          <p className="text-xs text-gray-400 italic">No comments yet</p>
        ) : (
          <div className="space-y-2">
            {comments.map((c) => (
              <div
                key={c.id}
                className="bg-gray-50 rounded-md p-2 text-xs border border-gray-100"
              >
                <div className="flex items-baseline justify-between gap-1 mb-0.5">
                  <span className="font-medium text-gray-700 truncate">
                    {c.task_title}
                  </span>
                  <span className="text-gray-400 text-[10px] flex-shrink-0">
                    {formatTime(c.created_at)}
                  </span>
                </div>
                <p className="text-gray-600 whitespace-pre-wrap break-words">
                  {c.content}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
