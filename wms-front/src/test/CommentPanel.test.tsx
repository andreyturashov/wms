import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { CommentPanel } from '../components/CommentPanel';
import { mockComment } from './fixtures';

// Mock the API module
vi.mock('../api', () => ({
  commentsApi: {
    getByAuthor: vi.fn(),
  },
}));

import { commentsApi } from '../api';

const mockGetByAuthor = vi.mocked(commentsApi.getByAuthor);

describe('CommentPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns null when no selection', () => {
    const { container } = render(<CommentPanel selection={null} />);
    expect(container.firstChild).toBeNull();
  });

  it('shows title with user name when user is selected', async () => {
    mockGetByAuthor.mockResolvedValueOnce([]);
    render(
      <CommentPanel
        selection={{ type: 'user', id: 'user-1', name: 'alice' }}
      />,
    );
    expect(screen.getByText(/Comments by alice/)).toBeInTheDocument();
  });

  it('shows title with agent name when agent is selected', async () => {
    mockGetByAuthor.mockResolvedValueOnce([]);
    render(
      <CommentPanel
        selection={{ type: 'agent', id: 'agent-1', name: 'Assistant Agent' }}
      />,
    );
    expect(screen.getByText(/Comments by Assistant Agent/)).toBeInTheDocument();
  });

  it('shows loading state', () => {
    mockGetByAuthor.mockReturnValueOnce(new Promise(() => {})); // never resolves
    render(
      <CommentPanel
        selection={{ type: 'user', id: 'user-1', name: 'alice' }}
      />,
    );
    expect(screen.getByText('Loading…')).toBeInTheDocument();
  });

  it('displays fetched comments', async () => {
    mockGetByAuthor.mockResolvedValueOnce([mockComment]);
    render(
      <CommentPanel
        selection={{ type: 'user', id: 'user-1', name: 'alice' }}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText('This needs urgent attention.')).toBeInTheDocument();
    });
  });

  it('shows task title in comment card', async () => {
    mockGetByAuthor.mockResolvedValueOnce([mockComment]);
    render(
      <CommentPanel
        selection={{ type: 'user', id: 'user-1', name: 'alice' }}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText('Fix login bug')).toBeInTheDocument();
    });
  });

  it('shows "No comments yet" when empty', async () => {
    mockGetByAuthor.mockResolvedValueOnce([]);
    render(
      <CommentPanel
        selection={{ type: 'user', id: 'user-1', name: 'alice' }}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText('No comments yet')).toBeInTheDocument();
    });
  });

  it('fetches with user_id param for user selection', async () => {
    mockGetByAuthor.mockResolvedValueOnce([]);
    render(
      <CommentPanel
        selection={{ type: 'user', id: 'user-1', name: 'alice' }}
      />,
    );

    await waitFor(() => {
      expect(mockGetByAuthor).toHaveBeenCalledWith({ user_id: 'user-1' });
    });
  });

  it('fetches with agent_id param for agent selection', async () => {
    mockGetByAuthor.mockResolvedValueOnce([]);
    render(
      <CommentPanel
        selection={{ type: 'agent', id: 'agent-1', name: 'Assistant Agent' }}
      />,
    );

    await waitFor(() => {
      expect(mockGetByAuthor).toHaveBeenCalledWith({ agent_id: 'agent-1' });
    });
  });

  it('shows user icon for user selection', () => {
    mockGetByAuthor.mockResolvedValueOnce([]);
    render(
      <CommentPanel
        selection={{ type: 'user', id: 'user-1', name: 'alice' }}
      />,
    );
    expect(screen.getByText(/👤/)).toBeInTheDocument();
  });

  it('shows agent icon for agent selection', () => {
    mockGetByAuthor.mockResolvedValueOnce([]);
    render(
      <CommentPanel
        selection={{ type: 'agent', id: 'agent-1', name: 'Assistant Agent' }}
      />,
    );
    expect(screen.getByText(/🤖/)).toBeInTheDocument();
  });
});
