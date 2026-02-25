import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TaskModal } from '../components/TaskModal';
import { mockTask, mockUser, mockUser2, mockAgent } from './fixtures';

describe('TaskModal', () => {
  const defaultProps = {
    isOpen: true,
    onClose: vi.fn(),
    onSubmit: vi.fn(),
    task: null,
    agents: [mockAgent],
    users: [mockUser, mockUser2],
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns null when not open', () => {
    const { container } = render(<TaskModal {...defaultProps} isOpen={false} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders create mode title when no task', () => {
    render(<TaskModal {...defaultProps} />);
    expect(screen.getByText('Create New Task')).toBeInTheDocument();
  });

  it('renders edit mode title when task is provided', () => {
    render(<TaskModal {...defaultProps} task={mockTask} />);
    expect(screen.getByText('Edit Task')).toBeInTheDocument();
  });

  it('populates form with task data in edit mode', () => {
    render(<TaskModal {...defaultProps} task={mockTask} />);

    const titleInput = screen.getByLabelText('Title') as HTMLInputElement;
    expect(titleInput.value).toBe('Fix login bug');

    const descArea = screen.getByLabelText('Description') as HTMLTextAreaElement;
    expect(descArea.value).toBe('Users cannot log in with special characters');
  });

  it('has empty form in create mode', () => {
    render(<TaskModal {...defaultProps} />);

    const titleInput = screen.getByLabelText('Title') as HTMLInputElement;
    expect(titleInput.value).toBe('');
  });

  it('renders status select with options', () => {
    render(<TaskModal {...defaultProps} />);
    expect(screen.getByLabelText('Status')).toBeInTheDocument();
    expect(screen.getByText('To Do')).toBeInTheDocument();
    expect(screen.getByText('In Progress')).toBeInTheDocument();
    expect(screen.getByText('Done')).toBeInTheDocument();
  });

  it('renders priority select with options', () => {
    render(<TaskModal {...defaultProps} />);
    expect(screen.getByLabelText('Priority')).toBeInTheDocument();
    expect(screen.getByText('Low')).toBeInTheDocument();
    expect(screen.getByText('Medium')).toBeInTheDocument();
    expect(screen.getByText('High')).toBeInTheDocument();
  });

  it('renders assignee select with users and agents', () => {
    render(<TaskModal {...defaultProps} />);
    const assigneeSelect = screen.getByLabelText('Assignee');
    expect(assigneeSelect).toBeInTheDocument();
    expect(screen.getByText('Unassigned')).toBeInTheDocument();
    expect(screen.getByText('alice')).toBeInTheDocument();
    expect(screen.getByText('bob')).toBeInTheDocument();
    expect(screen.getByText('Assistant Agent')).toBeInTheDocument();
  });

  it('calls onSubmit with form data on submit', async () => {
    const user = userEvent.setup();
    render(<TaskModal {...defaultProps} />);

    const titleInput = screen.getByLabelText('Title');
    await user.type(titleInput, 'New task title');

    const submitBtn = screen.getByText('Create');
    await user.click(submitBtn);

    expect(defaultProps.onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        title: 'New task title',
        status: 'todo',
        priority: 'medium',
      }),
    );
    expect(defaultProps.onClose).toHaveBeenCalled();
  });

  it('calls onClose when Cancel is clicked', async () => {
    const user = userEvent.setup();
    render(<TaskModal {...defaultProps} />);

    await user.click(screen.getByText('Cancel'));
    expect(defaultProps.onClose).toHaveBeenCalled();
  });

  it('shows Update button in edit mode', () => {
    render(<TaskModal {...defaultProps} task={mockTask} />);
    expect(screen.getByText('Update')).toBeInTheDocument();
  });

  it('submits with agent_id when agent is selected', async () => {
    const user = userEvent.setup();
    render(<TaskModal {...defaultProps} />);

    await user.type(screen.getByLabelText('Title'), 'Task');
    await user.selectOptions(screen.getByLabelText('Assignee'), 'agent:agent-1');
    await user.click(screen.getByText('Create'));

    expect(defaultProps.onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        agent_id: 'agent-1',
        assigned_user_id: null,
      }),
    );
  });

  it('submits with assigned_user_id when user is selected', async () => {
    const user = userEvent.setup();
    render(<TaskModal {...defaultProps} />);

    await user.type(screen.getByLabelText('Title'), 'Task');
    await user.selectOptions(screen.getByLabelText('Assignee'), 'user:user-2');
    await user.click(screen.getByText('Create'));

    expect(defaultProps.onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        agent_id: null,
        assigned_user_id: 'user-2',
      }),
    );
  });

  it('renders due date input', () => {
    render(<TaskModal {...defaultProps} />);
    expect(screen.getByLabelText('Due Date')).toBeInTheDocument();
  });
});
