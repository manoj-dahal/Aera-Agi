import { describe, expect, it } from 'vitest';
import { formatBytes, formatDuration, formatNumber, formatUptime, timeAgo, truncate, titleCase } from '@utils/format';
import { extractCodeBlocks, renderMarkdown } from '@utils/markdown';
import { cn } from '@utils/cn';

describe('format helpers', () => {
  it('formats bytes', () => {
    expect(formatBytes(0)).toBe('0 B');
    expect(formatBytes(512)).toBe('512 B');
    expect(formatBytes(2048)).toBe('2.0 KB');
    expect(formatBytes(5_242_880)).toBe('5.0 MB');
  });

  it('formats compact numbers', () => {
    expect(formatNumber(42)).toBe('42');
    expect(formatNumber(1500)).toBe('1.5k');
    expect(formatNumber(2_500_000)).toBe('2.5M');
  });

  it('formats durations', () => {
    expect(formatDuration(250)).toBe('250ms');
    expect(formatDuration(1500)).toBe('1.5s');
    expect(formatDuration(90_000)).toBe('1m 30s');
  });

  it('formats uptime', () => {
    expect(formatUptime(30)).toBe('30s');
    expect(formatUptime(300)).toBe('5m');
    expect(formatUptime(7200)).toBe('2h 0m');
    expect(formatUptime(172_800)).toBe('2d 0h');
  });

  it('renders relative time', () => {
    const now = Date.now() / 1000;
    expect(timeAgo(now)).toBe('just now');
    expect(timeAgo(now - 120)).toBe('2m ago');
    expect(timeAgo(now - 7200)).toBe('2h ago');
  });

  it('truncates and title-cases', () => {
    expect(truncate('a'.repeat(200), 10)).toHaveLength(10);
    expect(truncate('short', 10)).toBe('short');
    expect(titleCase('memory_graph')).toBe('Memory Graph');
  });
});

describe('markdown renderer', () => {
  it('escapes HTML to prevent injection', () => {
    const html = renderMarkdown('<script>alert("xss")</script>');
    expect(html).not.toContain('<script>');
    expect(html).toContain('&lt;script&gt;');
  });

  it('escapes HTML inside code fences', () => {
    const html = renderMarkdown('```html\n<img src=x onerror=alert(1)>\n```');
    expect(html).not.toContain('<img src=x');
    expect(html).toContain('&lt;img');
  });

  it('renders fenced code blocks', () => {
    const html = renderMarkdown('```python\nx = 1\n```');
    expect(html).toContain('<pre data-lang="python">');
    expect(html).toContain('x = 1');
  });

  it('renders inline code and bold', () => {
    expect(renderMarkdown('use `npm run build`')).toContain('<code>npm run build</code>');
    expect(renderMarkdown('**important**')).toContain('<strong>important</strong>');
  });

  it('extracts code blocks with languages', () => {
    const blocks = extractCodeBlocks('a\n```ts\nconst x = 1;\n```\nb\n```\nplain\n```');
    expect(blocks).toHaveLength(2);
    expect(blocks[0]).toEqual({ language: 'ts', code: 'const x = 1;' });
    expect(blocks[1]?.language).toBe('text');
  });

  it('returns no blocks when there is no code', () => {
    expect(extractCodeBlocks('just prose')).toEqual([]);
  });
});

describe('cn', () => {
  it('merges conditional classes', () => {
    expect(cn('a', false && 'b', 'c')).toBe('a c');
    expect(cn('a', undefined, null, 'd')).toBe('a d');
  });
});
