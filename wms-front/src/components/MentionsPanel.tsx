import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import type { Agent, Comment, User } from '../types';
import { commentsApi } from '../api';
import { MentionTextarea, renderMentionContent } from './MentionTextarea';

interface MentionsPanelProps {
  agents: Agent[];
  users: User[];
  currentUser: User | null;
}

export function MentionsPanel({ agents, users, currentUser }: MentionsPanelProps) {
  const [comments, setComments] = useState<Comment[]>([]);
  const [loading, setLoading] = useState(false);
  const [replyingTo, setReplyingTo] = useState<string | null>(null);
  const [replyContent, setReplyContent] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const loadMentions = useCallback(async () => {
    setLoading(true);
    try {
      const data = await commentsApi.getMentioningMe();
      setComments(data);
    } catch (err) {
      console.error('Failed to load mentions:', err);
      setComments([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadMentions();
  }, [loadMentions]);

  const handleReply = async (comment: Comment) => {
    if (!replyContent.trim() || submitting) return;
    setSubmitting(true);
    try {
      await commentsApi.create(comment.task_id, {
        content: replyContent.trim(),
        parent_id: comment.id,
      });
      setReplyContent('');
      setReplyingTo(null);
      await loadMentions();
    } catch (err) {
      console.error('Failed to post reply:', err);
    } finally {
      setSubmitting(false);
    }
  };

  const handleReplyKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>, comment: Comment) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      void handleReply(comment);
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

  return (
    <div className="flex-1 bg-white rounded-lg shadow-md overflow-hidden flex flex-col max-h-[calc(100vh-8rem)]">
      <div className="p-3 border-b border-gray-200">
        <h3 className="text-sm font-semibold text-gray-700">
          📬 Mentions of @{currentUser?.username ?? 'you'}
        </h3>
      </div>

      <div className="flex-1 overflow-y-auto p-3">
        {loading ? (
          <p className="text-xs text-gray-400">Loading…</p>
        ) : comments.length === 0 ? (
          <p className="text-xs text-gray-400 italic">No mentions yet</p>
        ) : (
          <div className="space-y-2">
            {comments.map((c) => (
              <div
                key={c.id}
                className="group bg-gray-50 rounded-md p-2 text-xs border border-gray-100"
              >
                <div className="flex items-baseline justify-between gap-1 mb-0.5">
                  <div className="flex items-baseline gap-1.5 min-w-0">
                    <span className="text-gray-500 flex-shrink-0">
                      {c.author_type === 'agent' ? '🤖' : '👤'} {c.author_name}
                    </span>
                    <span className="text-gray-300">·</span>
                    <Link
                      to={`/tasks/${c.task_id}`}
                      className="font-medium text-blue-600 hover:text-blue-800 hover:underline truncate"
                      title={`Open task: ${c.task_title}`}
                    >
                      {c.task_title}
                    </Link>
                  </div>
                  <span className="text-gray-400 text-[10px] flex-shrink-0">
                    {formatTime(c.created_at)}
                  </span>
                </div>
                <p className="text-gray-600 whitespace-pre-wrap break-words">
                  {renderMentionContent(c.content, users, agents)}
                </p>
                {/* Reply button */}
                {currentUser && (
                  <button
                    onClick={() => {
                      setReplyingTo(replyingTo === c.id ? null : c.id);
                      setReplyContent('');
                    }}
                    className="mt-1 opacity-0 group-hover:opacity-100 text-gray-400 hover:text-blue-500 transition-opacity text-[10px]"
                    title="Reply to this comment"
                  >
                    ↩ Reply
                  </button>
                )}
                {/* Inline reply form */}
                {replyingTo === c.id && (
                  <div className="mt-2 border-t border-gray-200 pt-2">
                    <div className="relative">
                      <MentionTextarea
                        value={replyContent}
                        onChange={setReplyContent}
                        onKeyDown={(e) => handleReplyKeyDown(e, c)}
                        placeholder={`Reply to ${c.author_name}…`}
                        rows={2}
                        className="w-full text-xs px-3 py-2 pr-16 border border-gray-200 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-blue-400 focus:border-transparent bg-gray-50 placeholder-gray-400"
                        users={users}
                        agents={agents}
                      />
                      <button
                        onClick={() => void handleReply(c)}
                        disabled={submitting || !replyContent.trim()}
                        className="absolute right-2 bottom-2 text-[10px] font-medium px-2 py-0.5 text-white bg-blue-500 rounded-md hover:bg-blue-600 disabled:opacity-40 transition-colors"
                      >
                        {submitting ? '…' : 'Reply'}
                      </button>
                    </div>
                    <div className="flex justify-between items-center mt-1">
                      <span className="text-[10px] text-gray-400">⌘+Enter to send</span>
                      <button
                        onClick={() => {
                          setReplyingTo(null);
                          setReplyContent('');
                        }}
                        className="text-[10px] px-2 py-0.5 text-gray-500 hover:text-gray-700"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
