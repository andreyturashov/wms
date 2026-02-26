import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { MentionTextarea, renderMentionContent } from '../components/MentionTextarea';
import { mockUser, mockUser2, mockAgent, mockAgent2 } from './fixtures';

/** Stateful wrapper so controlled textarea works with userEvent.type */
function Wrapper(props: Omit<React.ComponentProps<typeof MentionTextarea>, 'value' | 'onChange'>) {
  const [value, setValue] = useState('');
  return <MentionTextarea {...props} value={value} onChange={setValue} />;
}

describe('MentionTextarea', () => {
  const defaultProps = {
    value: '',
    onChange: vi.fn(),
    users: [mockUser, mockUser2],
    agents: [mockAgent, mockAgent2],
  };

  it('renders a textarea', () => {
    render(<MentionTextarea {...defaultProps} />);
    expect(screen.getByRole('textbox')).toBeInTheDocument();
  });

  it('displays the value', () => {
    render(<MentionTextarea {...defaultProps} value="Hello" />);
    expect(screen.getByRole('textbox')).toHaveValue('Hello');
  });

  it('renders placeholder', () => {
    render(<MentionTextarea {...defaultProps} placeholder="Type here…" />);
    expect(screen.getByPlaceholderText('Type here…')).toBeInTheDocument();
  });

  it('calls onChange on input', async () => {
    const onChange = vi.fn();
    render(<MentionTextarea {...defaultProps} onChange={onChange} />);
    const textarea = screen.getByRole('textbox');
    await userEvent.setup().type(textarea, 'Hi');
    expect(onChange).toHaveBeenCalled();
  });

  it('shows dropdown when @ is typed', async () => {
    const user = userEvent.setup();
    let value = '';
    const onChange = vi.fn((v: string) => {
      value = v;
    });
    const { rerender } = render(<MentionTextarea {...defaultProps} value={value} onChange={onChange} />);

    const textarea = screen.getByRole('textbox');
    await user.type(textarea, '@');

    // Rerender with updated value
    value = onChange.mock.calls[onChange.mock.calls.length - 1][0];
    rerender(<MentionTextarea {...defaultProps} value={value} onChange={onChange} />);

    // Should show the dropdown with all users and agents
    expect(screen.getByRole('listbox')).toBeInTheDocument();
    expect(screen.getByText('alice')).toBeInTheDocument();
    expect(screen.getByText('bob')).toBeInTheDocument();
    expect(screen.getByText('Assistant Agent')).toBeInTheDocument();
    expect(screen.getByText('Analytics Agent')).toBeInTheDocument();
  });

  it('filters suggestions as user types after @', async () => {
    const user = userEvent.setup();
    render(<Wrapper users={defaultProps.users} agents={defaultProps.agents} />);

    const textarea = screen.getByRole('textbox');
    await user.type(textarea, '@ali');

    expect(screen.getByRole('listbox')).toBeInTheDocument();
    expect(screen.getByText('alice')).toBeInTheDocument();
    // bob and agents should not match "ali"
    expect(screen.queryByText('bob')).not.toBeInTheDocument();
  });

  it('hides dropdown when no suggestions match', async () => {
    const user = userEvent.setup();
    render(<Wrapper users={defaultProps.users} agents={defaultProps.agents} />);

    const textarea = screen.getByRole('textbox');
    await user.type(textarea, '@zzz');

    // No listbox should be shown (no suggestions match)
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
  });

  it('shows user/agent type labels in dropdown', async () => {
    const user = userEvent.setup();
    let value = '';
    const onChange = vi.fn((v: string) => {
      value = v;
    });
    const { rerender } = render(<MentionTextarea {...defaultProps} value={value} onChange={onChange} />);

    const textarea = screen.getByRole('textbox');
    await user.type(textarea, '@');

    value = onChange.mock.calls[onChange.mock.calls.length - 1][0];
    rerender(<MentionTextarea {...defaultProps} value={value} onChange={onChange} />);

    // Check type labels are shown
    const options = screen.getAllByRole('option');
    expect(options.length).toBe(4); // 2 users + 2 agents
  });

  it('shows user and agent icons in dropdown', async () => {
    const user = userEvent.setup();
    let value = '';
    const onChange = vi.fn((v: string) => {
      value = v;
    });
    const { rerender } = render(<MentionTextarea {...defaultProps} value={value} onChange={onChange} />);

    const textarea = screen.getByRole('textbox');
    await user.type(textarea, '@');

    value = onChange.mock.calls[onChange.mock.calls.length - 1][0];
    rerender(<MentionTextarea {...defaultProps} value={value} onChange={onChange} />);

    expect(screen.getAllByText('👤').length).toBe(2);
    expect(screen.getAllByText('🤖').length).toBe(2);
  });

  it('does not show dropdown for @ in the middle of a word', async () => {
    const user = userEvent.setup();
    render(<Wrapper users={defaultProps.users} agents={defaultProps.agents} />);

    const textarea = screen.getByRole('textbox');
    await user.type(textarea, 'email@');

    // @ preceded by a non-space character should not trigger dropdown
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
  });

  it('closes dropdown on Escape', async () => {
    const user = userEvent.setup();
    let value = '';
    const onChange = vi.fn((v: string) => {
      value = v;
    });
    const { rerender } = render(<MentionTextarea {...defaultProps} value={value} onChange={onChange} />);

    const textarea = screen.getByRole('textbox');
    await user.type(textarea, '@');

    value = onChange.mock.calls[onChange.mock.calls.length - 1][0];
    rerender(<MentionTextarea {...defaultProps} value={value} onChange={onChange} />);

    expect(screen.getByRole('listbox')).toBeInTheDocument();

    await user.keyboard('{Escape}');

    expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
  });
});

describe('renderMentionContent', () => {
  const users = [mockUser, mockUser2];
  const agents = [mockAgent, mockAgent2];

  it('returns plain text when no mentions', () => {
    const nodes = renderMentionContent('Hello world', users, agents);
    expect(nodes).toEqual(['Hello world']);
  });

  it('highlights a user mention', () => {
    const { container } = render(
      <p>{renderMentionContent('Hello @alice!', users, agents)}</p>,
    );
    const mention = container.querySelector('.text-blue-600');
    expect(mention).not.toBeNull();
    expect(mention?.textContent).toBe('@alice');
  });

  it('highlights an agent mention', () => {
    const { container } = render(
      <p>{renderMentionContent('Ask @Assistant Agent for help', users, agents)}</p>,
    );
    const mention = container.querySelector('.text-blue-600');
    expect(mention).not.toBeNull();
    expect(mention?.textContent).toBe('@Assistant Agent');
  });

  it('highlights multiple mentions', () => {
    const { container } = render(
      <p>{renderMentionContent('@alice and @bob should review', users, agents)}</p>,
    );
    const mentions = container.querySelectorAll('.text-blue-600');
    expect(mentions.length).toBe(2);
    expect(mentions[0].textContent).toBe('@alice');
    expect(mentions[1].textContent).toBe('@bob');
  });

  it('does not highlight unknown mentions', () => {
    const { container } = render(
      <p>{renderMentionContent('Hello @unknown', users, agents)}</p>,
    );
    const mentions = container.querySelectorAll('.text-blue-600');
    expect(mentions.length).toBe(0);
  });

  it('returns content as-is when no users/agents provided', () => {
    const nodes = renderMentionContent('Hello @alice', [], []);
    expect(nodes).toEqual(['Hello @alice']);
  });

  it('preserves text around mentions', () => {
    const { container } = render(
      <p>{renderMentionContent('Hey @alice, check this out', users, agents)}</p>,
    );
    expect(container.textContent).toBe('Hey @alice, check this out');
  });
});
