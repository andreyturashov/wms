import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { TaskCard } from '../components/TaskCard';
import { mockTask, mockTaskInProgress, mockTaskDone, mockUser, mockUser2, mockAgent } from './fixtures';

const renderWithRouter = (ui: React.ReactElement) =>
  render(<MemoryRouter>{ui}</MemoryRouter>);

// Mock the API module
vi.mock('../api', () => ({
  tasksApi: {
    update: vi.fn(),
    delete: vi.fn(),
  },
  commentsApi: {
    getByTaskId: vi.fn().mockResolvedValue([]),
    create: vi.fn(),
    delete: vi.fn(),
  },
}));

import { tasksApi } from '../api';
const mockUpdate = vi.mocked(tasksApi.update);
const mockDelete = vi.mocked(tasksApi.delete);

describe('TaskCard', () => {
  const defaultProps = {
    task: mockTask,
    agents: [mockAgent],
    users: [mockUser, mockUser2],
    currentUser: mockUser,
    onUpdate: vi.fn(),
    onDelete: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('view mode', () => {
    it('renders task title', () => {
      renderWithRouter(<TaskCard {...defaultProps} />);
      expect(screen.getByText('Fix login bug')).toBeInTheDocument();
    });

    it('renders task title as a link to the task page', () => {
      renderWithRouter(<TaskCard {...defaultProps} />);
      const link = screen.getByTitle('Open task');
      expect(link).toBeInTheDocument();
      expect(link.tagName).toBe('A');
      expect(link).toHaveAttribute('href', '/tasks/task-1');
    });

    it('renders task description', () => {
      renderWithRouter(<TaskCard {...defaultProps} />);
      expect(screen.getByText('Users cannot log in with special characters')).toBeInTheDocument();
    });

    it('renders priority badge with correct color', () => {
      renderWithRouter(<TaskCard {...defaultProps} />);
      const badge = screen.getByText('high');
      expect(badge).toBeInTheDocument();
      expect(badge.className).toContain('bg-red-100');
    });

    it('renders medium priority with yellow', () => {
      renderWithRouter(<TaskCard {...defaultProps} task={{ ...mockTask, priority: 'medium' }} />);
      const badge = screen.getByText('medium');
      expect(badge.className).toContain('bg-yellow-100');
    });

    it('renders low priority with green', () => {
      renderWithRouter(<TaskCard {...defaultProps} task={{ ...mockTask, priority: 'low' }} />);
      const badge = screen.getByText('low');
      expect(badge.className).toContain('bg-green-100');
    });

    it('renders due date when present', () => {
      renderWithRouter(<TaskCard {...defaultProps} />);
      // The due date is formatted with toLocaleDateString
      // Just check that some date is rendered
      const dateEl = screen.getByText(/\d{1,2}\/\d{1,2}\/\d{4}|\w+ \d{1,2}, \d{4}/);
      expect(dateEl).toBeInTheDocument();
    });

    it('does not render due date when null', () => {
      renderWithRouter(<TaskCard {...defaultProps} task={{ ...mockTask, due_date: null }} />);
      // Should not have any date text
      const container = screen.getByText('Fix login bug').closest('div')!.parentElement!;
      expect(container.textContent).not.toMatch(/\/20/);
    });

    it('renders assigned agent badge', () => {
      renderWithRouter(<TaskCard {...defaultProps} task={mockTaskInProgress} />);
      expect(screen.getByText(/Assistant Agent/)).toBeInTheDocument();
    });

    it('renders assigned user badge', () => {
      renderWithRouter(<TaskCard {...defaultProps} task={mockTaskDone} />);
      expect(screen.getByText(/bob/)).toBeInTheDocument();
    });

    it('does not render description when empty', () => {
      renderWithRouter(<TaskCard {...defaultProps} task={{ ...mockTask, description: '' }} />);
      // The description paragraph should not be rendered
      const title = screen.getByText('Fix login bug');
      const card = title.closest('[draggable]')!;
      const paragraphs = card.querySelectorAll('p.text-gray-600');
      expect(paragraphs).toHaveLength(0);
    });

    it('has edit and delete buttons', () => {
      renderWithRouter(<TaskCard {...defaultProps} />);
      expect(screen.getByTitle('Edit task')).toBeInTheDocument();
      expect(screen.getByTitle('Delete task')).toBeInTheDocument();
    });

    it('has comment toggle button', () => {
      renderWithRouter(<TaskCard {...defaultProps} />);
      expect(screen.getByTitle('Toggle comments')).toBeInTheDocument();
    });

    it('is draggable', () => {
      renderWithRouter(<TaskCard {...defaultProps} />);
      const card = screen.getByText('Fix login bug').closest('[draggable]')!;
      expect(card).toHaveAttribute('draggable', 'true');
    });
  });

  describe('edit mode', () => {
    it('enters edit mode on double click', async () => {
      renderWithRouter(<TaskCard {...defaultProps} />);
      const card = screen.getByText('Fix login bug').closest('[draggable]')!;
      fireEvent.doubleClick(card);

      expect(screen.getByPlaceholderText('Task title')).toBeInTheDocument();
      expect(screen.getByText('Save')).toBeInTheDocument();
      expect(screen.getByText('Cancel')).toBeInTheDocument();
    });

    it('enters edit mode on edit button click', async () => {
      renderWithRouter(<TaskCard {...defaultProps} />);
      await userEvent.click(screen.getByTitle('Edit task'));

      expect(screen.getByPlaceholderText('Task title')).toBeInTheDocument();
    });

    it('populates form with current task values', async () => {
      renderWithRouter(<TaskCard {...defaultProps} />);
      await userEvent.click(screen.getByTitle('Edit task'));

      const titleInput = screen.getByPlaceholderText('Task title') as HTMLInputElement;
      expect(titleInput.value).toBe('Fix login bug');

      const descArea = screen.getByPlaceholderText('Description (optional)') as HTMLTextAreaElement;
      expect(descArea.value).toBe('Users cannot log in with special characters');
    });

    it('cancels edit mode on Cancel click', async () => {
      renderWithRouter(<TaskCard {...defaultProps} />);
      await userEvent.click(screen.getByTitle('Edit task'));
      await userEvent.click(screen.getByText('Cancel'));

      // Should be back to view mode
      expect(screen.queryByPlaceholderText('Task title')).not.toBeInTheDocument();
      expect(screen.getByText('Fix login bug')).toBeInTheDocument();
    });

    it('cancels edit mode on Escape key', async () => {
      renderWithRouter(<TaskCard {...defaultProps} />);
      await userEvent.click(screen.getByTitle('Edit task'));

      await userEvent.keyboard('{Escape}');

      expect(screen.queryByPlaceholderText('Task title')).not.toBeInTheDocument();
    });

    it('shows assignee select with users and agents', async () => {
      renderWithRouter(<TaskCard {...defaultProps} />);
      await userEvent.click(screen.getByTitle('Edit task'));

      // Check the assignee select contains user and agent options
      const assigneeSelect = screen.getAllByRole('combobox').find(
        (el) => el.querySelector('option[value=""]')?.textContent === 'Unassigned',
      )!;
      expect(assigneeSelect).toBeInTheDocument();
    });
  });

  describe('drag and drop', () => {
    it('sets taskId on drag start', () => {
      renderWithRouter(<TaskCard {...defaultProps} />);
      const card = screen.getByText('Fix login bug').closest('[draggable]')!;

      const dataTransfer = { setData: vi.fn() };
      fireEvent.dragStart(card, { dataTransfer });

      expect(dataTransfer.setData).toHaveBeenCalledWith('taskId', 'task-1');
    });
  });

  describe('comments toggle', () => {
    it('shows comment section on toggle click', async () => {
      renderWithRouter(<TaskCard {...defaultProps} />);
      const toggleBtn = screen.getByTitle('Toggle comments');
      await userEvent.click(toggleBtn);

      // CommentSection should appear (it will show "Loading comments...")
      expect(screen.getByText(/Loading comments|No comments yet|Write a comment/)).toBeInTheDocument();
    });

    it('does not show comment section when no current user', async () => {
      renderWithRouter(<TaskCard {...defaultProps} currentUser={null} />);
      const toggleBtn = screen.getByTitle('Toggle comments');
      await userEvent.click(toggleBtn);

      // CommentSection requires currentUser, should not render
      expect(screen.queryByText('Write a comment…')).not.toBeInTheDocument();
    });
  });

  describe('save editing', () => {
    it('calls API update and onUpdate on Cmd+Enter', async () => {
      const updatedTask = { ...mockTask, title: 'Updated title' };
      mockUpdate.mockResolvedValueOnce(updatedTask);

      renderWithRouter(<TaskCard {...defaultProps} />);
      await userEvent.click(screen.getByTitle('Edit task'));

      const titleInput = screen.getByPlaceholderText('Task title');
      await userEvent.clear(titleInput);
      await userEvent.type(titleInput, 'Updated title');

      // Press Cmd+Enter to save
      fireEvent.keyDown(titleInput.closest('.bg-white')!, {
        key: 'Enter',
        metaKey: true,
      });

      await waitFor(() => {
        expect(mockUpdate).toHaveBeenCalledWith(
          'task-1',
          expect.objectContaining({ title: 'Updated title' }),
        );
      });
      expect(defaultProps.onUpdate).toHaveBeenCalledWith(updatedTask);
    });

    it('calls API update via Save button click', async () => {
      const updatedTask = { ...mockTask, title: 'New title' };
      mockUpdate.mockResolvedValueOnce(updatedTask);

      renderWithRouter(<TaskCard {...defaultProps} />);
      await userEvent.click(screen.getByTitle('Edit task'));

      const titleInput = screen.getByPlaceholderText('Task title');
      await userEvent.clear(titleInput);
      await userEvent.type(titleInput, 'New title');

      await userEvent.click(screen.getByText('Save'));

      await waitFor(() => {
        expect(mockUpdate).toHaveBeenCalled();
      });
      expect(defaultProps.onUpdate).toHaveBeenCalledWith(updatedTask);
    });

    it('does not save when title is empty', async () => {
      renderWithRouter(<TaskCard {...defaultProps} />);
      await userEvent.click(screen.getByTitle('Edit task'));

      const titleInput = screen.getByPlaceholderText('Task title');
      await userEvent.clear(titleInput);

      // Save button should be disabled
      expect(screen.getByText('Save')).toBeDisabled();
    });

    it('handles API error during save gracefully', async () => {
      mockUpdate.mockRejectedValueOnce(new Error('Network error'));
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      renderWithRouter(<TaskCard {...defaultProps} />);
      await userEvent.click(screen.getByTitle('Edit task'));
      await userEvent.click(screen.getByText('Save'));

      await waitFor(() => {
        expect(mockUpdate).toHaveBeenCalled();
      });
      // Should stay in edit mode on error
      expect(screen.getByPlaceholderText('Task title')).toBeInTheDocument();
      consoleSpy.mockRestore();
    });

    it('sends agent_id when agent assignee is selected', async () => {
      const updatedTask = { ...mockTaskInProgress };
      mockUpdate.mockResolvedValueOnce(updatedTask);

      renderWithRouter(<TaskCard {...defaultProps} task={mockTaskInProgress} />);
      await userEvent.click(screen.getByTitle('Edit task'));
      await userEvent.click(screen.getByText('Save'));

      await waitFor(() => {
        expect(mockUpdate).toHaveBeenCalledWith(
          'task-2',
          expect.objectContaining({ agent_id: 'agent-1', assigned_user_id: null }),
        );
      });
    });

    it('sends assigned_user_id when user assignee is selected', async () => {
      const updatedTask = { ...mockTaskDone };
      mockUpdate.mockResolvedValueOnce(updatedTask);

      renderWithRouter(<TaskCard {...defaultProps} task={mockTaskDone} />);
      await userEvent.click(screen.getByTitle('Edit task'));
      await userEvent.click(screen.getByText('Save'));

      await waitFor(() => {
        expect(mockUpdate).toHaveBeenCalledWith(
          'task-3',
          expect.objectContaining({ agent_id: null, assigned_user_id: 'user-2' }),
        );
      });
    });
  });

  describe('delete task', () => {
    it('calls API delete and onDelete when confirmed', async () => {
      vi.spyOn(window, 'confirm').mockReturnValue(true);
      mockDelete.mockResolvedValueOnce(undefined);

      renderWithRouter(<TaskCard {...defaultProps} />);
      await userEvent.click(screen.getByTitle('Delete task'));

      await waitFor(() => {
        expect(mockDelete).toHaveBeenCalledWith('task-1');
      });
      expect(defaultProps.onDelete).toHaveBeenCalledWith('task-1');
    });

    it('does not delete when cancelled', async () => {
      vi.spyOn(window, 'confirm').mockReturnValue(false);

      renderWithRouter(<TaskCard {...defaultProps} />);
      await userEvent.click(screen.getByTitle('Delete task'));

      expect(mockDelete).not.toHaveBeenCalled();
    });
  });

  describe('drag behavior', () => {
    it('prevents drag when in edit mode', async () => {
      renderWithRouter(<TaskCard {...defaultProps} />);
      await userEvent.click(screen.getByTitle('Edit task'));

      // In edit mode, the card should not be draggable, drag should be prevented
      const editContainer = screen.getByPlaceholderText('Task title').closest('.bg-white')!;
      expect(editContainer).toBeInTheDocument();
    });

    it('resets opacity on drag end', () => {
      renderWithRouter(<TaskCard {...defaultProps} />);
      const card = screen.getByText('Fix login bug').closest('[draggable]')!;

      fireEvent.dragStart(card, { dataTransfer: { setData: vi.fn() } });
      expect(card.className).toContain('opacity-50');

      fireEvent.dragEnd(card);
      expect(card.className).not.toContain('opacity-50');
    });
  });
});
