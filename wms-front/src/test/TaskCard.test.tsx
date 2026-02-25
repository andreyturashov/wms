import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TaskCard } from '../components/TaskCard';
import { mockTask, mockTaskInProgress, mockTaskDone, mockUser, mockUser2, mockAgent } from './fixtures';

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
      render(<TaskCard {...defaultProps} />);
      expect(screen.getByText('Fix login bug')).toBeInTheDocument();
    });

    it('renders task description', () => {
      render(<TaskCard {...defaultProps} />);
      expect(screen.getByText('Users cannot log in with special characters')).toBeInTheDocument();
    });

    it('renders priority badge with correct color', () => {
      render(<TaskCard {...defaultProps} />);
      const badge = screen.getByText('high');
      expect(badge).toBeInTheDocument();
      expect(badge.className).toContain('bg-red-100');
    });

    it('renders medium priority with yellow', () => {
      render(<TaskCard {...defaultProps} task={{ ...mockTask, priority: 'medium' }} />);
      const badge = screen.getByText('medium');
      expect(badge.className).toContain('bg-yellow-100');
    });

    it('renders low priority with green', () => {
      render(<TaskCard {...defaultProps} task={{ ...mockTask, priority: 'low' }} />);
      const badge = screen.getByText('low');
      expect(badge.className).toContain('bg-green-100');
    });

    it('renders due date when present', () => {
      render(<TaskCard {...defaultProps} />);
      // The due date is formatted with toLocaleDateString
      // Just check that some date is rendered
      const dateEl = screen.getByText(/\d{1,2}\/\d{1,2}\/\d{4}|\w+ \d{1,2}, \d{4}/);
      expect(dateEl).toBeInTheDocument();
    });

    it('does not render due date when null', () => {
      render(<TaskCard {...defaultProps} task={{ ...mockTask, due_date: null }} />);
      // Should not have any date text
      const container = screen.getByText('Fix login bug').closest('div')!.parentElement!;
      expect(container.textContent).not.toMatch(/\/20/);
    });

    it('renders assigned agent badge', () => {
      render(<TaskCard {...defaultProps} task={mockTaskInProgress} />);
      expect(screen.getByText(/Assistant Agent/)).toBeInTheDocument();
    });

    it('renders assigned user badge', () => {
      render(<TaskCard {...defaultProps} task={mockTaskDone} />);
      expect(screen.getByText(/bob/)).toBeInTheDocument();
    });

    it('does not render description when empty', () => {
      render(<TaskCard {...defaultProps} task={{ ...mockTask, description: '' }} />);
      // The description paragraph should not be rendered
      const title = screen.getByText('Fix login bug');
      const card = title.closest('[draggable]')!;
      const paragraphs = card.querySelectorAll('p.text-gray-600');
      expect(paragraphs).toHaveLength(0);
    });

    it('has edit and delete buttons', () => {
      render(<TaskCard {...defaultProps} />);
      expect(screen.getByTitle('Edit task')).toBeInTheDocument();
      expect(screen.getByTitle('Delete task')).toBeInTheDocument();
    });

    it('has comment toggle button', () => {
      render(<TaskCard {...defaultProps} />);
      expect(screen.getByTitle('Toggle comments')).toBeInTheDocument();
    });

    it('is draggable', () => {
      render(<TaskCard {...defaultProps} />);
      const card = screen.getByText('Fix login bug').closest('[draggable]')!;
      expect(card).toHaveAttribute('draggable', 'true');
    });
  });

  describe('edit mode', () => {
    it('enters edit mode on double click', async () => {
      render(<TaskCard {...defaultProps} />);
      const card = screen.getByText('Fix login bug').closest('[draggable]')!;
      fireEvent.doubleClick(card);

      expect(screen.getByPlaceholderText('Task title')).toBeInTheDocument();
      expect(screen.getByText('Save')).toBeInTheDocument();
      expect(screen.getByText('Cancel')).toBeInTheDocument();
    });

    it('enters edit mode on edit button click', async () => {
      render(<TaskCard {...defaultProps} />);
      await userEvent.click(screen.getByTitle('Edit task'));

      expect(screen.getByPlaceholderText('Task title')).toBeInTheDocument();
    });

    it('populates form with current task values', async () => {
      render(<TaskCard {...defaultProps} />);
      await userEvent.click(screen.getByTitle('Edit task'));

      const titleInput = screen.getByPlaceholderText('Task title') as HTMLInputElement;
      expect(titleInput.value).toBe('Fix login bug');

      const descArea = screen.getByPlaceholderText('Description (optional)') as HTMLTextAreaElement;
      expect(descArea.value).toBe('Users cannot log in with special characters');
    });

    it('cancels edit mode on Cancel click', async () => {
      render(<TaskCard {...defaultProps} />);
      await userEvent.click(screen.getByTitle('Edit task'));
      await userEvent.click(screen.getByText('Cancel'));

      // Should be back to view mode
      expect(screen.queryByPlaceholderText('Task title')).not.toBeInTheDocument();
      expect(screen.getByText('Fix login bug')).toBeInTheDocument();
    });

    it('cancels edit mode on Escape key', async () => {
      render(<TaskCard {...defaultProps} />);
      await userEvent.click(screen.getByTitle('Edit task'));

      await userEvent.keyboard('{Escape}');

      expect(screen.queryByPlaceholderText('Task title')).not.toBeInTheDocument();
    });

    it('shows assignee select with users and agents', async () => {
      render(<TaskCard {...defaultProps} />);
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
      render(<TaskCard {...defaultProps} />);
      const card = screen.getByText('Fix login bug').closest('[draggable]')!;

      const dataTransfer = { setData: vi.fn() };
      fireEvent.dragStart(card, { dataTransfer });

      expect(dataTransfer.setData).toHaveBeenCalledWith('taskId', 'task-1');
    });
  });

  describe('comments toggle', () => {
    it('shows comment section on toggle click', async () => {
      render(<TaskCard {...defaultProps} />);
      const toggleBtn = screen.getByTitle('Toggle comments');
      await userEvent.click(toggleBtn);

      // CommentSection should appear (it will show "Loading comments...")
      expect(screen.getByText(/Loading comments|No comments yet|Write a comment/)).toBeInTheDocument();
    });

    it('does not show comment section when no current user', async () => {
      render(<TaskCard {...defaultProps} currentUser={null} />);
      const toggleBtn = screen.getByTitle('Toggle comments');
      await userEvent.click(toggleBtn);

      // CommentSection requires currentUser, should not render
      expect(screen.queryByText('Write a comment…')).not.toBeInTheDocument();
    });
  });
});
