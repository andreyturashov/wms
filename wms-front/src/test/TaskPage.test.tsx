import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { TaskPage } from '../components/TaskPage';
import { mockTask, mockUser, mockUser2, mockAgent } from './fixtures';

vi.mock('../api', () => ({
  tasksApi: {
    getById: vi.fn(),
  },
  agentsApi: {
    getAll: vi.fn(),
  },
  usersApi: {
    getAll: vi.fn(),
  },
  authApi: {
    me: vi.fn(),
  },
  commentsApi: {
    getByTaskId: vi.fn().mockResolvedValue([]),
    create: vi.fn(),
    delete: vi.fn(),
  },
}));

import { tasksApi, agentsApi, usersApi, authApi } from '../api';

const mockGetById = vi.mocked(tasksApi.getById);
const mockGetAgents = vi.mocked(agentsApi.getAll);
const mockGetUsers = vi.mocked(usersApi.getAll);
const mockMe = vi.mocked(authApi.me);

function renderTaskPage(taskId: string = 'task-1') {
  return render(
    <MemoryRouter initialEntries={[`/tasks/${taskId}`]}>
      <Routes>
        <Route path="/tasks/:taskId" element={<TaskPage />} />
        <Route path="/" element={<div>Board</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('TaskPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetById.mockResolvedValue(mockTask);
    mockGetAgents.mockResolvedValue([mockAgent]);
    mockGetUsers.mockResolvedValue([mockUser, mockUser2]);
    mockMe.mockResolvedValue(mockUser);
  });

  it('shows loading state initially', () => {
    mockGetById.mockReturnValue(new Promise(() => {}));
    renderTaskPage();
    expect(screen.getByText('Loading task…')).toBeInTheDocument();
  });

  it('renders task title after loading', async () => {
    renderTaskPage();
    await waitFor(() => {
      expect(screen.getByText('Fix login bug')).toBeInTheDocument();
    });
  });

  it('renders task description', async () => {
    renderTaskPage();
    await waitFor(() => {
      expect(screen.getByText('Users cannot log in with special characters')).toBeInTheDocument();
    });
  });

  it('renders status badge', async () => {
    renderTaskPage();
    await waitFor(() => {
      expect(screen.getByText('To Do')).toBeInTheDocument();
    });
  });

  it('renders priority badge', async () => {
    renderTaskPage();
    await waitFor(() => {
      expect(screen.getByText('high priority')).toBeInTheDocument();
    });
  });

  it('shows "Back to Board" link', async () => {
    renderTaskPage();
    await waitFor(() => {
      expect(screen.getByText('← Board')).toBeInTheDocument();
    });
  });

  it('renders due date when present', async () => {
    renderTaskPage();
    await waitFor(() => {
      // Due date "2024-06-15" formatted by toLocaleDateString — multiple dates on page
      const dates = screen.getAllByText(/2024|6\/15|Jun/);
      expect(dates.length).toBeGreaterThanOrEqual(1);
    });
  });

  it('shows "No description" when description is empty', async () => {
    mockGetById.mockResolvedValue({ ...mockTask, description: '' });
    renderTaskPage();
    await waitFor(() => {
      expect(screen.getByText('No description')).toBeInTheDocument();
    });
  });

  it('shows Unassigned when no assignee', async () => {
    renderTaskPage();
    await waitFor(() => {
      expect(screen.getByText('Unassigned')).toBeInTheDocument();
    });
  });

  it('shows error when task not found', async () => {
    mockGetById.mockRejectedValue(new Error('Not found'));
    renderTaskPage('nonexistent');
    await waitFor(() => {
      expect(screen.getByText('Task not found or you are not authorized.')).toBeInTheDocument();
    });
  });

  it('shows "Back to Board" link on error page', async () => {
    mockGetById.mockRejectedValue(new Error('Not found'));
    renderTaskPage('nonexistent');
    await waitFor(() => {
      expect(screen.getByText('← Back to Board')).toBeInTheDocument();
    });
  });

  it('shows comment section', async () => {
    renderTaskPage();
    await waitFor(() => {
      expect(screen.getByText('Comments')).toBeInTheDocument();
    });
  });

  it('calls API with correct task ID', async () => {
    renderTaskPage('task-1');
    await waitFor(() => {
      expect(mockGetById).toHaveBeenCalledWith('task-1');
    });
  });

  it('shows assigned agent name', async () => {
    mockGetById.mockResolvedValue({ ...mockTask, agent_id: 'agent-1' });
    renderTaskPage();
    await waitFor(() => {
      expect(screen.getByText(/Assistant Agent/)).toBeInTheDocument();
    });
  });

  it('shows assigned user name', async () => {
    mockGetById.mockResolvedValue({ ...mockTask, assigned_user_id: 'user-2' });
    renderTaskPage();
    await waitFor(() => {
      expect(screen.getByText(/bob/)).toBeInTheDocument();
    });
  });

  it('shows "None" when no due date', async () => {
    mockGetById.mockResolvedValue({ ...mockTask, due_date: null });
    renderTaskPage();
    await waitFor(() => {
      expect(screen.getByText('None')).toBeInTheDocument();
    });
  });
});
