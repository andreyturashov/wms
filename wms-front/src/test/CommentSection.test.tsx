import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { CommentSection } from '../components/CommentSection';
import { mockUser, mockUser2, mockAgent, mockComment, mockCommentWithReplies } from './fixtures';

// Mock the API module
vi.mock('../api', () => ({
  commentsApi: {
    getByTaskId: vi.fn(),
    create: vi.fn(),
    delete: vi.fn(),
  },
}));

import { commentsApi } from '../api';

const mockGetByTaskId = vi.mocked(commentsApi.getByTaskId);
const mockCreate = vi.mocked(commentsApi.create);
const mockDelete = vi.mocked(commentsApi.delete);

describe('CommentSection', () => {
  const defaultProps = {
    taskId: 'task-1',
    agents: [mockAgent],
    users: [mockUser, mockUser2],
    currentUser: mockUser,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows loading state initially', () => {
    mockGetByTaskId.mockReturnValueOnce(new Promise(() => {}));
    render(<CommentSection {...defaultProps} />);
    expect(screen.getByText('Loading comments…')).toBeInTheDocument();
  });

  it('shows "No comments yet" when empty', async () => {
    mockGetByTaskId.mockResolvedValueOnce([]);
    render(<CommentSection {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('No comments yet')).toBeInTheDocument();
    });
  });

  it('renders comments after loading', async () => {
    mockGetByTaskId.mockResolvedValueOnce([mockComment]);
    render(<CommentSection {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('This needs urgent attention.')).toBeInTheDocument();
    });
  });

  it('displays author name', async () => {
    mockGetByTaskId.mockResolvedValueOnce([mockComment]);
    render(<CommentSection {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('alice')).toBeInTheDocument();
    });
  });

  it('renders user icon for user comments', async () => {
    mockGetByTaskId.mockResolvedValueOnce([mockComment]);
    render(<CommentSection {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('👤')).toBeInTheDocument();
    });
  });

  it('renders agent icon for agent comments', async () => {
    mockGetByTaskId.mockResolvedValueOnce([mockCommentWithReplies]);
    render(<CommentSection {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('🤖')).toBeInTheDocument();
    });
  });

  it('renders nested replies', async () => {
    mockGetByTaskId.mockResolvedValueOnce([mockCommentWithReplies]);
    render(<CommentSection {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('I am investigating.')).toBeInTheDocument();
      expect(screen.getByText('Thanks for looking into it!')).toBeInTheDocument();
    });
  });

  it('has a textarea for new comments', async () => {
    mockGetByTaskId.mockResolvedValueOnce([]);
    render(<CommentSection {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText('Write a comment… (type @ to mention)')).toBeInTheDocument();
    });
  });

  it('has a Send button', async () => {
    mockGetByTaskId.mockResolvedValueOnce([]);
    render(<CommentSection {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('Send')).toBeInTheDocument();
    });
  });

  it('Send button is disabled when textarea is empty', async () => {
    mockGetByTaskId.mockResolvedValueOnce([]);
    render(<CommentSection {...defaultProps} />);

    await waitFor(() => {
      const sendBtn = screen.getByText('Send');
      expect(sendBtn).toBeDisabled();
    });
  });

  it('submits a new comment', async () => {
    const user = userEvent.setup();
    const newComment = {
      ...mockComment,
      id: 'new-comment',
      content: 'Hello world',
    };
    mockGetByTaskId.mockResolvedValueOnce([]);
    mockCreate.mockResolvedValueOnce(newComment);

    render(<CommentSection {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText('Write a comment… (type @ to mention)')).toBeInTheDocument();
    });

    const textarea = screen.getByPlaceholderText('Write a comment… (type @ to mention)');
    await user.type(textarea, 'Hello world');
    await user.click(screen.getByText('Send'));

    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalledWith('task-1', {
        content: 'Hello world',
        agent_id: null,
        parent_id: null,
      });
    });

    // New comment should appear in the list
    await waitFor(() => {
      expect(screen.getByText('Hello world')).toBeInTheDocument();
    });
  });

  it('shows reply indicator when replying', async () => {
    const user = userEvent.setup();
    mockGetByTaskId.mockResolvedValueOnce([mockComment]);

    render(<CommentSection {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('This needs urgent attention.')).toBeInTheDocument();
    });

    // Click reply button (↩)
    const replyBtn = screen.getByTitle('Reply');
    await user.click(replyBtn);

    expect(screen.getByText(/Replying to/)).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Reply to alice…')).toBeInTheDocument();
  });

  it('cancels reply on dismiss', async () => {
    const user = userEvent.setup();
    mockGetByTaskId.mockResolvedValueOnce([mockComment]);

    render(<CommentSection {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('This needs urgent attention.')).toBeInTheDocument();
    });

    const replyBtn = screen.getByTitle('Reply');
    await user.click(replyBtn);

    expect(screen.getByText(/Replying to/)).toBeInTheDocument();

    // Click the dismiss button (✕) next to the reply indicator
    const dismissBtns = screen.getAllByText('✕');
    // The dismiss button is the one inside the reply indicator (not the delete buttons)
    const replyDismiss = dismissBtns.find(
      (btn) => btn.closest('.text-blue-600') || btn.closest('[class*="blue"]'),
    );
    if (replyDismiss) {
      await user.click(replyDismiss);
    }

    // Reply indicator should be gone, placeholder resets
    await waitFor(() => {
      expect(screen.getByPlaceholderText('Write a comment… (type @ to mention)')).toBeInTheDocument();
    });
  });

  it('shows "Post as" select with agents', async () => {
    mockGetByTaskId.mockResolvedValueOnce([]);
    render(<CommentSection {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText(`Post as ${mockUser.username}`)).toBeInTheDocument();
      expect(screen.getByText(`Post as ${mockAgent.name}`)).toBeInTheDocument();
    });
  });

  it('shows reply button on hover text', async () => {
    mockGetByTaskId.mockResolvedValueOnce([mockComment]);

    render(<CommentSection {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByTitle('Reply')).toBeInTheDocument();
    });
  });

  it('shows delete button for comments', async () => {
    mockGetByTaskId.mockResolvedValueOnce([mockComment]);
    render(<CommentSection {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByTitle('Delete comment')).toBeInTheDocument();
    });
  });

  it('deletes a comment', async () => {
    const user = userEvent.setup();
    mockGetByTaskId.mockResolvedValueOnce([mockComment]);
    mockDelete.mockResolvedValueOnce(undefined);

    render(<CommentSection {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('This needs urgent attention.')).toBeInTheDocument();
    });

    await user.click(screen.getByTitle('Delete comment'));

    await waitFor(() => {
      expect(mockDelete).toHaveBeenCalledWith('task-1', 'comment-1');
    });

    // Comment should be removed
    await waitFor(() => {
      expect(screen.queryByText('This needs urgent attention.')).not.toBeInTheDocument();
    });
  });

  it('changes button to Reply when in reply mode', async () => {
    const user = userEvent.setup();
    mockGetByTaskId.mockResolvedValueOnce([mockComment]);

    render(<CommentSection {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('Send')).toBeInTheDocument();
    });

    await user.click(screen.getByTitle('Reply'));

    expect(screen.getByText('Reply')).toBeInTheDocument();
  });

  it('submits a reply and nests it under parent', async () => {
    const user = userEvent.setup();
    const reply = {
      ...mockComment,
      id: 'reply-1',
      content: 'Noted!',
      parent_id: mockComment.id,
      replies: [],
    };
    mockGetByTaskId.mockResolvedValueOnce([mockComment]);
    mockCreate.mockResolvedValueOnce(reply);

    render(<CommentSection {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('This needs urgent attention.')).toBeInTheDocument();
    });

    // Click reply
    await user.click(screen.getByTitle('Reply'));

    const textarea = screen.getByPlaceholderText('Reply to alice…');
    await user.type(textarea, 'Noted!');
    await user.click(screen.getByText('Reply'));

    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalledWith('task-1', {
        content: 'Noted!',
        agent_id: null,
        parent_id: 'comment-1',
      });
    });

    // Reply should be visible
    await waitFor(() => {
      expect(screen.getByText('Noted!')).toBeInTheDocument();
    });
  });

  it('submits comment via Cmd+Enter', async () => {
    const user = userEvent.setup();
    const newComment = {
      ...mockComment,
      id: 'cmd-enter-comment',
      content: 'Quick comment',
    };
    mockGetByTaskId.mockResolvedValueOnce([]);
    mockCreate.mockResolvedValueOnce(newComment);

    render(<CommentSection {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText('Write a comment… (type @ to mention)')).toBeInTheDocument();
    });

    const textarea = screen.getByPlaceholderText('Write a comment… (type @ to mention)');
    await user.type(textarea, 'Quick comment');

    // Fire Cmd+Enter
    fireEvent.keyDown(textarea, { key: 'Enter', metaKey: true });

    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalledWith('task-1', {
        content: 'Quick comment',
        agent_id: null,
        parent_id: null,
      });
    });
  });

  it('submits as agent when agent is selected in "Post as"', async () => {
    const user = userEvent.setup();
    const agentComment = {
      ...mockComment,
      id: 'agent-comment',
      content: 'Agent says hi',
      agent_id: 'agent-1',
      user_id: null,
      author_type: 'agent' as const,
      author_name: 'Executor Agent',
    };
    mockGetByTaskId.mockResolvedValueOnce([]);
    mockCreate.mockResolvedValueOnce(agentComment);

    render(<CommentSection {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText('Write a comment… (type @ to mention)')).toBeInTheDocument();
    });

    // Select agent in "Post as" dropdown
    const postAsSelect = screen.getByRole('combobox');
    await user.selectOptions(postAsSelect, `agent:${mockAgent.id}`);

    const textarea = screen.getByPlaceholderText('Write a comment… (type @ to mention)');
    await user.type(textarea, 'Agent says hi');
    await user.click(screen.getByText('Send'));

    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalledWith('task-1', {
        content: 'Agent says hi',
        agent_id: 'agent-1',
        parent_id: null,
      });
    });
  });

  it('handles error when loading comments fails', async () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    mockGetByTaskId.mockRejectedValueOnce(new Error('Network error'));

    render(<CommentSection {...defaultProps} />);

    // Should eventually show empty state
    await waitFor(() => {
      expect(screen.queryByText('Loading comments…')).not.toBeInTheDocument();
    });
    consoleSpy.mockRestore();
  });

  it('handles error when posting comment fails', async () => {
    const user = userEvent.setup();
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    mockGetByTaskId.mockResolvedValueOnce([]);
    mockCreate.mockRejectedValueOnce(new Error('Post failed'));

    render(<CommentSection {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText('Write a comment… (type @ to mention)')).toBeInTheDocument();
    });

    const textarea = screen.getByPlaceholderText('Write a comment… (type @ to mention)');
    await user.type(textarea, 'Will fail');
    await user.click(screen.getByText('Send'));

    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalled();
    });
    consoleSpy.mockRestore();
  });

  it('handles error when deleting comment fails', async () => {
    const user = userEvent.setup();
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    mockGetByTaskId.mockResolvedValueOnce([mockComment]);
    mockDelete.mockRejectedValueOnce(new Error('Delete failed'));

    render(<CommentSection {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByTitle('Delete comment')).toBeInTheDocument();
    });

    await user.click(screen.getByTitle('Delete comment'));

    await waitFor(() => {
      expect(mockDelete).toHaveBeenCalled();
    });
    // Comment should still be visible since delete failed
    expect(screen.getByText('This needs urgent attention.')).toBeInTheDocument();
    consoleSpy.mockRestore();
  });
});
