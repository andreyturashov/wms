import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Sidebar } from '../components/Sidebar';
import { mockUser, mockUser2, mockAgent, mockAgent2 } from './fixtures';

describe('Sidebar', () => {
  const defaultProps = {
    users: [mockUser, mockUser2],
    agents: [mockAgent, mockAgent2],
    selection: null,
    onSelect: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders Users heading', () => {
    render(<Sidebar {...defaultProps} />);
    expect(screen.getByText('Users')).toBeInTheDocument();
  });

  it('renders Agents heading', () => {
    render(<Sidebar {...defaultProps} />);
    expect(screen.getByText('Agents')).toBeInTheDocument();
  });

  it('renders all user names', () => {
    render(<Sidebar {...defaultProps} />);
    expect(screen.getByText('alice')).toBeInTheDocument();
    expect(screen.getByText('bob')).toBeInTheDocument();
  });

  it('renders all agent names', () => {
    render(<Sidebar {...defaultProps} />);
    expect(screen.getByText('Assistant Agent')).toBeInTheDocument();
    expect(screen.getByText('Analytics Agent')).toBeInTheDocument();
  });

  it('calls onSelect with user info on click', async () => {
    const user = userEvent.setup();
    render(<Sidebar {...defaultProps} />);

    await user.click(screen.getByText('alice'));

    expect(defaultProps.onSelect).toHaveBeenCalledWith({
      type: 'user',
      id: 'user-1',
      name: 'alice',
    });
  });

  it('calls onSelect with agent info on click', async () => {
    const user = userEvent.setup();
    render(<Sidebar {...defaultProps} />);

    await user.click(screen.getByText('Assistant Agent'));

    expect(defaultProps.onSelect).toHaveBeenCalledWith({
      type: 'agent',
      id: 'agent-1',
      name: 'Assistant Agent',
    });
  });

  it('toggles off when clicking the already-selected user', async () => {
    const user = userEvent.setup();
    render(
      <Sidebar
        {...defaultProps}
        selection={{ type: 'user', id: 'user-1', name: 'alice' }}
      />,
    );

    await user.click(screen.getByText('alice'));

    expect(defaultProps.onSelect).toHaveBeenCalledWith(null);
  });

  it('toggles off when clicking the already-selected agent', async () => {
    const user = userEvent.setup();
    render(
      <Sidebar
        {...defaultProps}
        selection={{ type: 'agent', id: 'agent-1', name: 'Assistant Agent' }}
      />,
    );

    await user.click(screen.getByText('Assistant Agent'));

    expect(defaultProps.onSelect).toHaveBeenCalledWith(null);
  });

  it('highlights selected user', () => {
    render(
      <Sidebar
        {...defaultProps}
        selection={{ type: 'user', id: 'user-1', name: 'alice' }}
      />,
    );

    const aliceBtn = screen.getByText('alice').closest('button')!;
    expect(aliceBtn.className).toContain('bg-emerald-100');
  });

  it('highlights selected agent', () => {
    render(
      <Sidebar
        {...defaultProps}
        selection={{ type: 'agent', id: 'agent-1', name: 'Assistant Agent' }}
      />,
    );

    const agentBtn = screen.getByText('Assistant Agent').closest('button')!;
    expect(agentBtn.className).toContain('bg-indigo-100');
  });

  it('shows "No users" when users list is empty', () => {
    render(<Sidebar {...defaultProps} users={[]} />);
    expect(screen.getByText('No users')).toBeInTheDocument();
  });

  it('shows "No agents" when agents list is empty', () => {
    render(<Sidebar {...defaultProps} agents={[]} />);
    expect(screen.getByText('No agents')).toBeInTheDocument();
  });
});
