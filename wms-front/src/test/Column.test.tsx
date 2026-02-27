import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { Column } from '../components/Column';
import { mockTask, mockTaskInProgress, mockUser, mockAgent } from './fixtures';
import type { Task } from '../types';

const renderWithRouter = (ui: React.ReactElement) =>
  render(<MemoryRouter>{ui}</MemoryRouter>);

describe('Column', () => {
  const defaultProps = {
    title: 'To Do',
    status: 'todo' as Task['status'],
    tasks: [mockTask],
    agents: [mockAgent],
    users: [mockUser],
    currentUser: mockUser,
    onUpdateTask: vi.fn(),
    onDeleteTask: vi.fn(),
    onDrop: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders column title and task count', () => {
    renderWithRouter(<Column {...defaultProps} />);
    expect(screen.getByText('To Do')).toBeInTheDocument();
    expect(screen.getByText('1')).toBeInTheDocument();
  });

  it('renders task cards for each task', () => {
    renderWithRouter(<Column {...defaultProps} />);
    expect(screen.getByText('Fix login bug')).toBeInTheDocument();
  });

  it('shows correct count with multiple tasks', () => {
    renderWithRouter(
      <Column
        {...defaultProps}
        tasks={[mockTask, { ...mockTaskInProgress, status: 'todo' }]}
      />,
    );
    expect(screen.getByText('2')).toBeInTheDocument();
  });

  it('renders empty column with zero count', () => {
    renderWithRouter(<Column {...defaultProps} tasks={[]} />);
    expect(screen.getByText('0')).toBeInTheDocument();
  });

  it('applies correct background color for todo status', () => {
    const { container } = renderWithRouter(<Column {...defaultProps} />);
    const col = container.firstChild as HTMLElement;
    expect(col.className).toContain('bg-gray-100');
  });

  it('applies correct background color for in_progress status', () => {
    const { container } = renderWithRouter(
      <Column {...defaultProps} title="In Progress" status="in_progress" />,
    );
    const col = container.firstChild as HTMLElement;
    expect(col.className).toContain('bg-blue-100');
  });

  it('applies correct background color for done status', () => {
    const { container } = renderWithRouter(
      <Column {...defaultProps} title="Done" status="done" />,
    );
    const col = container.firstChild as HTMLElement;
    expect(col.className).toContain('bg-green-100');
  });

  it('calls onDrop with taskId and new status on drop', () => {
    renderWithRouter(<Column {...defaultProps} />);
    const col = document.querySelector('.bg-gray-100')!;

    const dataTransfer = {
      getData: vi.fn().mockReturnValue('task-1'),
      preventDefault: vi.fn(),
    };
    fireEvent.drop(col, { dataTransfer });

    expect(defaultProps.onDrop).toHaveBeenCalledWith('task-1', 'todo');
  });

  it('does not call onDrop when no taskId in dataTransfer', () => {
    renderWithRouter(<Column {...defaultProps} />);
    const col = document.querySelector('.bg-gray-100')!;

    const dataTransfer = {
      getData: vi.fn().mockReturnValue(''),
      preventDefault: vi.fn(),
    };
    fireEvent.drop(col, { dataTransfer });

    expect(defaultProps.onDrop).not.toHaveBeenCalled();
  });

  it('prevents default on dragOver', () => {
    renderWithRouter(<Column {...defaultProps} />);
    const col = document.querySelector('.bg-gray-100')!;

    const event = new Event('dragover', { bubbles: true, cancelable: true });
    col.dispatchEvent(event);

    expect(event.defaultPrevented).toBe(true);
  });
});
