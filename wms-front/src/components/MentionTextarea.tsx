import { useEffect, useRef, useState, useCallback } from 'react';
import type { Agent, User } from '../types';

export interface MentionSuggestion {
  type: 'user' | 'agent';
  id: string;
  label: string;
}

interface MentionTextareaProps {
  value: string;
  onChange: (value: string) => void;
  onKeyDown?: (e: React.KeyboardEvent<HTMLTextAreaElement>) => void;
  placeholder?: string;
  rows?: number;
  className?: string;
  users: User[];
  agents: Agent[];
}

export function MentionTextarea({
  value,
  onChange,
  onKeyDown,
  placeholder,
  rows = 2,
  className,
  users,
  agents,
}: MentionTextareaProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const [showDropdown, setShowDropdown] = useState(false);
  const [filter, setFilter] = useState('');
  const [activeIndex, setActiveIndex] = useState(0);
  const [mentionStart, setMentionStart] = useState<number | null>(null);

  const buildSuggestions = useCallback((): MentionSuggestion[] => {
    const lowerFilter = filter.toLowerCase();
    const results: MentionSuggestion[] = [];

    for (const u of users) {
      if (u.username.toLowerCase().includes(lowerFilter)) {
        results.push({ type: 'user', id: u.id, label: u.username });
      }
    }
    for (const a of agents) {
      if (a.name.toLowerCase().includes(lowerFilter)) {
        results.push({ type: 'agent', id: a.id, label: a.name });
      }
    }

    return results;
  }, [users, agents, filter]);

  const suggestions = showDropdown ? buildSuggestions() : [];

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(e.target as Node) &&
        textareaRef.current &&
        !textareaRef.current.contains(e.target as Node)
      ) {
        setShowDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const insertMention = useCallback(
    (suggestion: MentionSuggestion) => {
      if (mentionStart === null) return;
      const before = value.slice(0, mentionStart);
      const after = value.slice(textareaRef.current?.selectionStart ?? value.length);
      const mentionText = `@${suggestion.label} `;
      const newValue = before + mentionText + after;
      onChange(newValue);
      setShowDropdown(false);
      setMentionStart(null);

      // Restore focus and cursor position
      requestAnimationFrame(() => {
        const pos = before.length + mentionText.length;
        textareaRef.current?.focus();
        textareaRef.current?.setSelectionRange(pos, pos);
      });
    },
    [mentionStart, value, onChange],
  );

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newValue = e.target.value;
    const cursorPos = e.target.selectionStart ?? 0;
    onChange(newValue);

    // Look backwards from cursor for an @ trigger
    const textBeforeCursor = newValue.slice(0, cursorPos);
    const atIndex = textBeforeCursor.lastIndexOf('@');

    if (atIndex >= 0) {
      // The @ must be at start or preceded by whitespace
      const charBefore = atIndex > 0 ? textBeforeCursor[atIndex - 1] : ' ';
      const textAfterAt = textBeforeCursor.slice(atIndex + 1);
      // No spaces in the query (if there's a space it's no longer a mention trigger)
      if (/\s/.test(charBefore) || atIndex === 0) {
        if (!/\s/.test(textAfterAt)) {
          setMentionStart(atIndex);
          setFilter(textAfterAt);
          setShowDropdown(true);
          setActiveIndex(0);
          return;
        }
      }
    }

    setShowDropdown(false);
    setMentionStart(null);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (showDropdown && suggestions.length > 0) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setActiveIndex((prev) => (prev + 1) % suggestions.length);
        return;
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault();
        setActiveIndex((prev) => (prev - 1 + suggestions.length) % suggestions.length);
        return;
      }
      if (e.key === 'Enter' || e.key === 'Tab') {
        e.preventDefault();
        insertMention(suggestions[activeIndex]);
        return;
      }
      if (e.key === 'Escape') {
        e.preventDefault();
        setShowDropdown(false);
        return;
      }
    }

    // Forward non-mention keypresses to parent handler
    onKeyDown?.(e);
  };

  return (
    <div className="relative">
      <textarea
        ref={textareaRef}
        value={value}
        onChange={handleInputChange}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        rows={rows}
        className={className}
      />
      {showDropdown && suggestions.length > 0 && (
        <div
          ref={dropdownRef}
          className="absolute bottom-full left-0 mb-1 w-56 max-h-40 overflow-y-auto bg-white border border-gray-200 rounded-md shadow-lg z-50"
          role="listbox"
          aria-label="Mention suggestions"
        >
          {suggestions.map((s, idx) => (
            <button
              key={`${s.type}:${s.id}`}
              role="option"
              aria-selected={idx === activeIndex}
              className={`w-full text-left px-3 py-1.5 text-xs flex items-center gap-2 ${
                idx === activeIndex ? 'bg-blue-50 text-blue-700' : 'text-gray-700 hover:bg-gray-50'
              }`}
              onMouseDown={(e) => {
                e.preventDefault(); // Prevent textarea blur
                insertMention(s);
              }}
              onMouseEnter={() => setActiveIndex(idx)}
            >
              <span className="flex-shrink-0">
                {s.type === 'agent' ? '🤖' : '👤'}
              </span>
              <span className="truncate">{s.label}</span>
              <span className="ml-auto text-[10px] text-gray-400">{s.type}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

/**
 * Parse comment content and return React nodes with highlighted @mentions.
 * Known mention names are highlighted; unknown `@word` are left as plain text.
 */
// eslint-disable-next-line react-refresh/only-export-components
export function renderMentionContent(
  content: string,
  users: User[],
  agents: Agent[],
): React.ReactNode[] {
  // Build a set of known names for highlighting
  const knownNames = new Set<string>();
  for (const u of users) knownNames.add(u.username.toLowerCase());
  for (const a of agents) knownNames.add(a.name.toLowerCase());

  // Match @Name patterns — names can contain letters, digits, spaces (for multi-word agent names)
  // We greedily match and then check against known names (longest match first)
  const sortedNames = [...knownNames].sort((a, b) => b.length - a.length);
  if (sortedNames.length === 0) {
    return [content];
  }

  // Escape regex special chars in names
  const escaped = sortedNames.map((n) => n.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
  const regex = new RegExp(`@(${escaped.join('|')})\\b`, 'gi');

  const parts: React.ReactNode[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = regex.exec(content)) !== null) {
    // Text before the mention
    if (match.index > lastIndex) {
      parts.push(content.slice(lastIndex, match.index));
    }
    // The mention itself
    parts.push(
      <span
        key={match.index}
        className="text-blue-600 font-medium bg-blue-50 rounded px-0.5"
      >
        @{match[1]}
      </span>,
    );
    lastIndex = regex.lastIndex;
  }

  // Remaining text
  if (lastIndex < content.length) {
    parts.push(content.slice(lastIndex));
  }

  return parts.length > 0 ? parts : [content];
}
