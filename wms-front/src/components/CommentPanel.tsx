import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import type { Agent, Comment, Task, User } from '../types';
import { commentsApi, tasksApi } from '../api';
import { MentionTextarea, renderMentionContent } from './MentionTextarea';

export type AuthorSelection =
  | { type: 'user'; id: string; name: string }
  | { type: 'agent'; id: string; name: string }
  | null;

interface CommentPanelProps {
  selection: AuthorSelection;
  agents: Agent[];
  users: User[];
  currentUser: User | null;
  onTaskCreated?: (task: Task) => void;
}

export function CommentPanel({ selection, agents, users, currentUser, onTaskCreated }: CommentPanelProps) {
  const [comments, setComments] = useState<Comment[]>([]);
  const [loading, setLoading] = useState(false);
  const [replyingTo, setReplyingTo] = useState<string | null>(null);
  const [replyContent, setReplyContent] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [taskContent, setTaskContent] = useState('');
  const [creatingTask, setCreatingTask] = useState(false);

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
      // Reload to see the reply
      if (selection) {
        const params =
          selection.type === 'user'
            ? { user_id: selection.id }
            : { agent_id: selection.id };
        const data = await commentsApi.getByAuthor(params);
        setComments(data);
      }
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

  const handleCreateTask = async () => {
    if (!taskContent.trim() || creatingTask || !selection) return;
    setCreatingTask(true);
    try {
      const lines = taskContent.trim().split('\n');
      const title = lines[0];
      const description = lines.slice(1).join('\n').trim();
      const newTask = await tasksApi.create({
        title,
        description,
        status: 'todo',
        priority: 'medium',
        agent_id: selection.type === 'agent' ? selection.id : null,
        assigned_user_id: selection.type === 'user' ? selection.id : null,
      });
      setTaskContent('');
      onTaskCreated?.(newTask);
    } catch (err) {
      console.error('Failed to create task:', err);
    } finally {
      setCreatingTask(false);
    }
  };

  const handleTaskKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      void handleCreateTask();
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
                className="group bg-gray-50 rounded-md p-2 text-xs border border-gray-100"
              >
                <div className="flex items-baseline justify-between gap-1 mb-0.5">
                  <Link
                    to={`/tasks/${c.task_id}`}
                    className="font-medium text-blue-600 hover:text-blue-800 hover:underline truncate"
                    title={`Open task: ${c.task_title}`}
                  >
                    {c.task_title}
                  </Link>
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
                    <MentionTextarea
                      value={replyContent}
                      onChange={setReplyContent}
                      onKeyDown={(e) => handleReplyKeyDown(e, c)}
                      placeholder={`Reply to ${c.author_name}…`}
                      rows={2}
                      className="w-full text-xs px-2 py-1 border border-gray-300 rounded-md resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
                      users={users}
                      agents={agents}
                    />
                    <div className="flex justify-end gap-1 mt-1">
                      <button
                        onClick={() => {
                          setReplyingTo(null);
                          setReplyContent('');
                        }}
                        className="text-[10px] px-2 py-0.5 text-gray-500 hover:text-gray-700"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={() => void handleReply(c)}
                        disabled={submitting || !replyContent.trim()}
                        className="text-[10px] px-2 py-0.5 text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50"
                      >
                        {submitting ? '…' : 'Reply'}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Create task form */}
      {currentUser && (
        <div className="p-3 border-t border-gray-200">
          <p className="text-[10px] text-gray-500 mb-1">
            Create a task assigned to {selection.name} (first line = title)
          </p>
          <textarea
            value={taskContent}
            onChange={(e) => setTaskContent(e.target.value)}
            onKeyDown={handleTaskKeyDown}
            placeholder={`Task title for ${selection.name}…\nOptional description`}
            rows={2}
            className="w-full text-xs px-2 py-1 border border-gray-300 rounded-md resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <div className="flex justify-end mt-1">
            <button
              onClick={() => void handleCreateTask()}
              disabled={creatingTask || !taskContent.trim()}
              className="text-xs px-2 py-0.5 text-white bg-green-600 rounded-md hover:bg-green-700 disabled:opacity-50"
            >
              {creatingTask ? '…' : '+ Create Task'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
