import { useEffect, useRef, useState } from 'react';
import type { Agent, Comment, User } from '../types';
import { commentsApi } from '../api';
import { MentionTextarea, renderMentionContent } from './MentionTextarea';

interface CommentSectionProps {
  taskId: string;
  agents: Agent[];
  users: User[];
  currentUser: User;
}

export function CommentSection({ taskId, agents, users, currentUser }: CommentSectionProps) {
  const [comments, setComments] = useState<Comment[]>([]);
  const [loading, setLoading] = useState(true);
  const [newContent, setNewContent] = useState('');
  const [postAs, setPostAs] = useState(''); // "" = current user, "agent:<id>" = agent
  const [submitting, setSubmitting] = useState(false);
  const [replyTo, setReplyTo] = useState<Comment | null>(null);
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

  /** Check if text contains an @mention that matches an active agent key */
  const mentionsAgent = (text: string) =>
    agents.some((a) => text.toLowerCase().includes(`@${a.key.toLowerCase()}`));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newContent.trim() || submitting) return;

    setSubmitting(true);
    try {
      const agentId = postAs.startsWith('agent:') ? postAs.slice(6) : null;
      const content = newContent.trim();
      const comment = await commentsApi.create(taskId, {
        content,
        agent_id: agentId,
        parent_id: replyTo?.id ?? null,
      });

      if (replyTo) {
        setComments((prev) => addReply(prev, replyTo.id, comment));
      } else {
        setComments((prev) => [...prev, comment]);
      }
      setNewContent('');
      setReplyTo(null);

      // Agent reply is generated in the background — poll briefly to pick it up
      if (!agentId && mentionsAgent(content)) {
        const poll = async (retries: number, delay: number) => {
          for (let i = 0; i < retries; i++) {
            await new Promise((r) => setTimeout(r, delay));
            const data = await commentsApi.getByTaskId(taskId);
            const updated = data.find((c: Comment) => c.id === comment.id);
            if (updated && updated.replies && updated.replies.length > 0) {
              setComments(data);
              return;
            }
          }
          // Final refresh even if no reply appeared yet
          const data = await commentsApi.getByTaskId(taskId);
          setComments(data);
        };
        void poll(10, 3000); // 10 attempts, 3 s apart (~30 s max)
      }
    } catch (err) {
      console.error('Failed to post comment:', err);
    } finally {
      setSubmitting(false);
    }
  };

  /** Recursively insert a reply under the matching parent */
  const addReply = (list: Comment[], parentId: string, reply: Comment): Comment[] =>
    list.map((c) =>
      c.id === parentId
        ? { ...c, replies: [...c.replies, reply] }
        : { ...c, replies: addReply(c.replies, parentId, reply) },
    );

  /** Recursively remove a comment by id */
  const removeComment = (list: Comment[], commentId: string): Comment[] =>
    list
      .filter((c) => c.id !== commentId)
      .map((c) => ({ ...c, replies: removeComment(c.replies, commentId) }));

  const handleDelete = async (commentId: string) => {
    try {
      await commentsApi.delete(taskId, commentId);
      setComments((prev) => removeComment(prev, commentId));
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

  /** Render a single comment + its nested replies */
  const renderComment = (c: Comment, depth: number = 0) => (
    <div key={c.id} style={{ marginLeft: depth * 20 }}>
      <div className="group flex gap-2 text-xs">
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
              onClick={() => setReplyTo(c)}
              className="ml-1 opacity-0 group-hover:opacity-100 text-gray-400 hover:text-blue-500 transition-opacity text-[10px]"
              title="Reply"
            >
              ↩
            </button>
            <button
              onClick={() => void handleDelete(c.id)}
              className="ml-auto opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-500 transition-opacity"
              title="Delete comment"
            >
              ✕
            </button>
          </div>
          <p className="text-gray-600 whitespace-pre-wrap break-words">{renderMentionContent(c.content, users, agents)}</p>
        </div>
      </div>
      {c.replies?.length > 0 && (
        <div className="mt-1 space-y-1 border-l-2 border-gray-200 pl-1">
          {c.replies.map((r) => renderComment(r, depth + 1))}
        </div>
      )}
    </div>
  );

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
        {comments.map((c) => renderComment(c))}
        <div ref={bottomRef} />
      </div>

      {/* Reply indicator */}
      {replyTo && (
        <div className="flex items-center gap-1 text-[11px] text-blue-600 mb-1">
          <span>↩ Replying to <strong>{replyTo.author_name}</strong></span>
          <button
            onClick={() => setReplyTo(null)}
            className="text-gray-400 hover:text-red-500 ml-1"
          >
            ✕
          </button>
        </div>
      )}

      {/* New comment form */}
      <form onSubmit={handleSubmit} className="flex flex-col gap-1">
        <div className="flex gap-1">
          <MentionTextarea
            value={newContent}
            onChange={setNewContent}
            onKeyDown={handleKeyDown}
            placeholder={replyTo ? `Reply to ${replyTo.author_name}…` : 'Write a comment… (type @ to mention)'}
            rows={2}
            className="flex-1 text-xs px-2 py-1 border border-gray-300 rounded-md resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
            users={users}
            agents={agents}
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
            {submitting ? '…' : replyTo ? 'Reply' : 'Send'}
          </button>
        </div>
      </form>
    </div>
  );
}
