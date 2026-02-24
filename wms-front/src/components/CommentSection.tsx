import { useEffect, useRef, useState } from 'react';
import type { Agent, Comment, User } from '../types';
import { commentsApi } from '../api';

interface CommentSectionProps {
  taskId: string;
  agents: Agent[];
  currentUser: User;
}

export function CommentSection({ taskId, agents, currentUser }: CommentSectionProps) {
  const [comments, setComments] = useState<Comment[]>([]);
  const [loading, setLoading] = useState(true);
  const [newContent, setNewContent] = useState('');
  const [postAs, setPostAs] = useState(''); // "" = current user, "agent:<id>" = agent
  const [submitting, setSubmitting] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const data = await commentsApi.getByTaskId(taskId);
        setComments(data);
      } catch (err) {
        console.error('Failed to load comments:', err);
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, [taskId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [comments.length]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newContent.trim() || submitting) return;

    setSubmitting(true);
    try {
      const agentId = postAs.startsWith('agent:') ? postAs.slice(6) : null;
      const comment = await commentsApi.create(taskId, {
        content: newContent.trim(),
        agent_id: agentId,
      });
      setComments((prev) => [...prev, comment]);
      setNewContent('');
    } catch (err) {
      console.error('Failed to post comment:', err);
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (commentId: string) => {
    try {
      await commentsApi.delete(taskId, commentId);
      setComments((prev) => prev.filter((c) => c.id !== commentId));
    } catch (err) {
      console.error('Failed to delete comment:', err);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      void handleSubmit(e);
    }
  };

  const formatTime = (iso: string) => {
    const d = new Date(iso);
    return d.toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (loading) {
    return <p className="text-xs text-gray-400 py-2">Loading comments…</p>;
  }

  return (
    <div className="mt-2 border-t border-gray-200 pt-2">
      {/* Comments list */}
      <div className="max-h-48 overflow-y-auto space-y-2 mb-2">
        {comments.length === 0 && (
          <p className="text-xs text-gray-400 italic">No comments yet</p>
        )}
        {comments.map((c) => (
          <div key={c.id} className="group flex gap-2 text-xs">
            <div className="flex-shrink-0 pt-0.5">
              {c.author_type === 'agent' ? (
                <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-indigo-100 text-indigo-700 text-[10px]">
                  🤖
                </span>
              ) : (
                <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-emerald-100 text-emerald-700 text-[10px]">
                  👤
                </span>
              )}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-baseline gap-1">
                <span className="font-medium text-gray-700">{c.author_name}</span>
                <span className="text-gray-400 text-[10px]">{formatTime(c.created_at)}</span>
                <button
                  onClick={() => void handleDelete(c.id)}
                  className="ml-auto opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-500 transition-opacity"
                  title="Delete comment"
                >
                  ✕
                </button>
              </div>
              <p className="text-gray-600 whitespace-pre-wrap break-words">{c.content}</p>
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* New comment form */}
      <form onSubmit={handleSubmit} className="flex flex-col gap-1">
        <div className="flex gap-1">
          <textarea
            value={newContent}
            onChange={(e) => setNewContent(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Write a comment…"
            rows={2}
            className="flex-1 text-xs px-2 py-1 border border-gray-300 rounded-md resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div className="flex items-center gap-2">
          <select
            value={postAs}
            onChange={(e) => setPostAs(e.target.value)}
            className="text-[11px] px-1.5 py-0.5 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="">Post as {currentUser.username}</option>
            {agents.map((a) => (
              <option key={a.id} value={`agent:${a.id}`}>
                Post as {a.name}
              </option>
            ))}
          </select>
          <button
            type="submit"
            disabled={submitting || !newContent.trim()}
            className="ml-auto text-xs px-2 py-0.5 text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50"
          >
            {submitting ? '…' : 'Send'}
          </button>
        </div>
      </form>
    </div>
  );
}
