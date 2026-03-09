import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { CommentPanel } from '../components/CommentPanel';
import { mockComment, mockTask, mockUser, mockUser2, mockAgent, mockAgent2 } from './fixtures';

// Mock the API module
vi.mock('../api', () => ({
  commentsApi: {
    getByAuthor: vi.fn(),
    create: vi.fn(),
  },
  tasksApi: {
    create: vi.fn(),
  },
}));

import { commentsApi, tasksApi } from '../api';

const mockGetByAuthor = vi.mocked(commentsApi.getByAuthor);
const mockCreate = vi.mocked(commentsApi.create);
const mockTaskCreate = vi.mocked(tasksApi.create);

const defaultProps = {
  agents: [mockAgent, mockAgent2],
  users: [mockUser, mockUser2],
  currentUser: mockUser,
};

const renderPanel = (props: Parameters<typeof CommentPanel>[0]) =>
  render(
    <MemoryRouter>
      <CommentPanel {...props} />
    </MemoryRouter>,
  );

describe('CommentPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns null when no selection', () => {
    const { container } = renderPanel({ selection: null, ...defaultProps });
    expect(container.firstChild).toBeNull();
  });

  it('shows title with user name when user is selected', async () => {
    mockGetByAuthor.mockResolvedValueOnce([]);
    renderPanel({
      selection: { type: 'user', id: 'user-1', name: 'alice' },
      ...defaultProps,
    });
    expect(screen.getByText(/Comments by alice/)).toBeInTheDocument();
  });

  it('shows title with agent name when agent is selected', async () => {
    mockGetByAuthor.mockResolvedValueOnce([]);
    renderPanel({
      selection: { type: 'agent', id: 'agent-1', name: 'Executor Agent' },
      ...defaultProps,
    });
    expect(screen.getByText(/Comments by Executor Agent/)).toBeInTheDocument();
  });

  it('shows loading state', () => {
    mockGetByAuthor.mockReturnValueOnce(new Promise(() => {})); // never resolves
    renderPanel({
      selection: { type: 'user', id: 'user-1', name: 'alice' },
      ...defaultProps,
    });
    expect(screen.getByText('Loading…')).toBeInTheDocument();
  });

  it('displays fetched comments', async () => {
    mockGetByAuthor.mockResolvedValueOnce([mockComment]);
    renderPanel({
      selection: { type: 'user', id: 'user-1', name: 'alice' },
      ...defaultProps,
    });

    await waitFor(() => {
      expect(screen.getByText('This needs urgent attention.')).toBeInTheDocument();
    });
  });

  it('shows task title as a link to the task page', async () => {
    mockGetByAuthor.mockResolvedValueOnce([mockComment]);
    renderPanel({
      selection: { type: 'user', id: 'user-1', name: 'alice' },
      ...defaultProps,
    });

    await waitFor(() => {
      const link = screen.getByRole('link', { name: /Fix login bug/ });
      expect(link).toBeInTheDocument();
      expect(link).toHaveAttribute('href', '/tasks/task-1');
    });
  });

  it('shows "No comments yet" when empty', async () => {
    mockGetByAuthor.mockResolvedValueOnce([]);
    renderPanel({
      selection: { type: 'user', id: 'user-1', name: 'alice' },
      ...defaultProps,
    });

    await waitFor(() => {
      expect(screen.getByText('No comments yet')).toBeInTheDocument();
    });
  });

  it('fetches with user_id param for user selection', async () => {
    mockGetByAuthor.mockResolvedValueOnce([]);
    renderPanel({
      selection: { type: 'user', id: 'user-1', name: 'alice' },
      ...defaultProps,
    });

    await waitFor(() => {
      expect(mockGetByAuthor).toHaveBeenCalledWith({ user_id: 'user-1' });
    });
  });

  it('fetches with agent_id param for agent selection', async () => {
    mockGetByAuthor.mockResolvedValueOnce([]);
    renderPanel({
      selection: { type: 'agent', id: 'agent-1', name: 'Executor Agent' },
      ...defaultProps,
    });

    await waitFor(() => {
      expect(mockGetByAuthor).toHaveBeenCalledWith({ agent_id: 'agent-1' });
    });
  });

  it('shows user icon for user selection', () => {
    mockGetByAuthor.mockResolvedValueOnce([]);
    renderPanel({
      selection: { type: 'user', id: 'user-1', name: 'alice' },
      ...defaultProps,
    });
    expect(screen.getByText(/👤/)).toBeInTheDocument();
  });

  it('shows agent icon for agent selection', () => {
    mockGetByAuthor.mockResolvedValueOnce([]);
    renderPanel({
      selection: { type: 'agent', id: 'agent-1', name: 'Executor Agent' },
      ...defaultProps,
    });
    expect(screen.getByText(/🤖/)).toBeInTheDocument();
  });

  it('shows reply button on hover and opens reply form', async () => {
    const user = userEvent.setup();
    mockGetByAuthor.mockResolvedValueOnce([mockComment]);
    renderPanel({
      selection: { type: 'user', id: 'user-1', name: 'alice' },
      ...defaultProps,
    });

    await waitFor(() => {
      expect(screen.getByText('This needs urgent attention.')).toBeInTheDocument();
    });

    // Click the reply button
    const replyBtn = screen.getByTitle('Reply to this comment');
    await user.click(replyBtn);

    // Reply form should appear
    expect(screen.getByPlaceholderText(/Reply to alice/)).toBeInTheDocument();
    expect(screen.getByText('Cancel')).toBeInTheDocument();
  });

  it('submits a reply and reloads comments', async () => {
    const user = userEvent.setup();
    const replyComment = {
      ...mockComment,
      id: 'comment-reply',
      content: 'Got it, thanks!',
      parent_id: mockComment.id,
    };
    mockGetByAuthor.mockResolvedValueOnce([mockComment]);
    mockCreate.mockResolvedValueOnce(replyComment);
    mockGetByAuthor.mockResolvedValueOnce([mockComment]); // reload after reply

    renderPanel({
      selection: { type: 'user', id: 'user-1', name: 'alice' },
      ...defaultProps,
    });

    await waitFor(() => {
      expect(screen.getByText('This needs urgent attention.')).toBeInTheDocument();
    });

    // Open reply form
    await user.click(screen.getByTitle('Reply to this comment'));
    const textarea = screen.getByPlaceholderText(/Reply to alice/);
    await user.type(textarea, 'Got it, thanks!');
    await user.click(screen.getByText('Reply'));

    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalledWith('task-1', {
        content: 'Got it, thanks!',
        parent_id: 'comment-1',
      });
    });
  });

  it('cancels reply and hides the form', async () => {
    const user = userEvent.setup();
    mockGetByAuthor.mockResolvedValueOnce([mockComment]);
    renderPanel({
      selection: { type: 'user', id: 'user-1', name: 'alice' },
      ...defaultProps,
    });

    await waitFor(() => {
      expect(screen.getByText('This needs urgent attention.')).toBeInTheDocument();
    });

    // Open then cancel
    await user.click(screen.getByTitle('Reply to this comment'));
    expect(screen.getByPlaceholderText(/Reply to alice/)).toBeInTheDocument();
    await user.click(screen.getByText('Cancel'));
    expect(screen.queryByPlaceholderText(/Reply to alice/)).not.toBeInTheDocument();
  });

  it('shows create task form when user is logged in', async () => {
    mockGetByAuthor.mockResolvedValueOnce([]);
    renderPanel({
      selection: { type: 'user', id: 'user-1', name: 'alice' },
      ...defaultProps,
    });

    await waitFor(() => {
      expect(screen.getByText(/Create a task assigned to alice/)).toBeInTheDocument();
    });
    expect(screen.getByPlaceholderText(/Task title for alice/)).toBeInTheDocument();
    expect(screen.getByText('+ Create')).toBeInTheDocument();
  });

  it('creates a task assigned to the selected user', async () => {
    const user = userEvent.setup();
    const onTaskCreated = vi.fn();
    mockGetByAuthor.mockResolvedValueOnce([]);
    mockTaskCreate.mockResolvedValueOnce(mockTask);

    renderPanel({
      selection: { type: 'user', id: 'user-1', name: 'alice' },
      ...defaultProps,
      onTaskCreated,
    });

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/Task title for alice/)).toBeInTheDocument();
    });

    const textarea = screen.getByPlaceholderText(/Task title for alice/);
    await user.type(textarea, 'New task title\nSome description');
    await user.click(screen.getByText('+ Create'));

    await waitFor(() => {
      expect(mockTaskCreate).toHaveBeenCalledWith({
        title: 'New task title',
        description: 'Some description',
        status: 'todo',
        priority: 'medium',
        agent_id: null,
        assigned_user_id: 'user-1',
      });
    });
    expect(onTaskCreated).toHaveBeenCalledWith(mockTask);
  });

  it('creates a task assigned to the selected agent', async () => {
    const user = userEvent.setup();
    const onTaskCreated = vi.fn();
    mockGetByAuthor.mockResolvedValueOnce([]);
    mockTaskCreate.mockResolvedValueOnce(mockTask);

    renderPanel({
      selection: { type: 'agent', id: 'agent-1', name: 'Executor Agent' },
      ...defaultProps,
      onTaskCreated,
    });

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/Task title for Executor Agent/)).toBeInTheDocument();
    });

    const textarea = screen.getByPlaceholderText(/Task title for Executor Agent/);
    await user.type(textarea, 'Agent task');
    await user.click(screen.getByText('+ Create'));

    await waitFor(() => {
      expect(mockTaskCreate).toHaveBeenCalledWith({
        title: 'Agent task',
        description: '',
        status: 'todo',
        priority: 'medium',
        agent_id: 'agent-1',
        assigned_user_id: null,
      });
    });
    expect(onTaskCreated).toHaveBeenCalledWith(mockTask);
  });

  it('disables create button when input is empty', async () => {
    mockGetByAuthor.mockResolvedValueOnce([]);
    renderPanel({
      selection: { type: 'user', id: 'user-1', name: 'alice' },
      ...defaultProps,
    });

    await waitFor(() => {
      expect(screen.getByText('+ Create')).toBeDisabled();
    });
  });
});
