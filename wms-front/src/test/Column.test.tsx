import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Column } from '../components/Column';
import { mockTask, mockTaskInProgress, mockUser, mockAgent } from './fixtures';
import type { Task } from '../types';

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

  it('renders column title and task count', () => {
    render(<Column {...defaultProps} />);
    expect(screen.getByText('To Do')).toBeInTheDocument();
    expect(screen.getByText('1')).toBeInTheDocument();
  });

  it('renders task cards for each task', () => {
    render(<Column {...defaultProps} />);
    expect(screen.getByText('Fix login bug')).toBeInTheDocument();
  });

  it('shows correct count with multiple tasks', () => {
    render(
      <Column
        {...defaultProps}
        tasks={[mockTask, { ...mockTaskInProgress, status: 'todo' }]}
      />,
    );
    expect(screen.getByText('2')).toBeInTheDocument();
  });

  it('renders empty column with zero count', () => {
    render(<Column {...defaultProps} tasks={[]} />);
    expect(screen.getByText('0')).toBeInTheDocument();
  });

  it('applies correct background color for todo status', () => {
    const { container } = render(<Column {...defaultProps} />);
    const col = container.firstChild as HTMLElement;
    expect(col.className).toContain('bg-gray-100');
  });

  it('applies correct background color for in_progress status', () => {
    const { container } = render(
      <Column {...defaultProps} title="In Progress" status="in_progress" />,
    );
    const col = container.firstChild as HTMLElement;
    expect(col.className).toContain('bg-blue-100');
  });

  it('applies correct background color for done status', () => {
    const { container } = render(
      <Column {...defaultProps} title="Done" status="done" />,
    );
    const col = container.firstChild as HTMLElement;
    expect(col.className).toContain('bg-green-100');
  });
});
