/**
 * Component behaviour, rendered for real.
 *
 * Every other suite in this directory reads source text, which cannot tell
 * whether a button is actually clickable or a loading state actually appears.
 * These mount the components in jsdom and interact with them.
 */

import { describe, expect, it, vi } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { Button, IconButton } from '@components/buttons/Button';
import { Card } from '@components/cards/Card';
import { EmptyState, ErrorState, LoadingState } from '@components/widgets/EmptyState';
import { StatusPill } from '@components/widgets/StatusPill';
import { Mark } from '@components/brand/Mark';
import { Input } from '@components/forms/Input';

describe('Button', () => {
  it('calls its handler when clicked', async () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Save</Button>);

    await userEvent.click(screen.getByRole('button', { name: 'Save' }));

    expect(onClick).toHaveBeenCalledOnce();
  });

  it('does not fire while disabled', async () => {
    const onClick = vi.fn();
    render(
      <Button onClick={onClick} disabled>
        Save
      </Button>,
    );

    await userEvent.click(screen.getByRole('button'));

    expect(onClick).not.toHaveBeenCalled();
  });

  it('blocks a second click while loading', async () => {
    // Without this a slow request could be fired twice by an impatient user.
    const onClick = vi.fn();
    render(
      <Button onClick={onClick} loading>
        Save
      </Button>,
    );

    await userEvent.click(screen.getByRole('button'));

    expect(screen.getByRole('button')).toBeDisabled();
    expect(onClick).not.toHaveBeenCalled();
  });

  it('shows a spinner instead of the icon while loading', () => {
    const { rerender } = render(
      <Button icon={<span data-testid="icon" />}>Go</Button>,
    );
    expect(screen.getByTestId('icon')).toBeTruthy();

    rerender(
      <Button icon={<span data-testid="icon" />} loading>
        Go
      </Button>,
    );

    expect(screen.queryByTestId('icon')).toBeNull();
  });

  it('keeps its label visible while loading', () => {
    // A button that blanks its text looks broken rather than busy.
    render(<Button loading>Uploading</Button>);

    expect(screen.getByRole('button')).toHaveTextContent('Uploading');
  });

  it.each(['primary', 'secondary', 'ghost', 'danger', 'subtle'] as const)(
    'renders the %s variant',
    (variant) => {
      render(<Button variant={variant}>X</Button>);
      expect(screen.getByRole('button').className).not.toBe('');
    },
  );

  it('IconButton requires an accessible name', () => {
    render(<IconButton aria-label="Close" />);

    expect(screen.getByRole('button', { name: 'Close' })).toBeTruthy();
  });
});

describe('state widgets', () => {
  it('LoadingState announces what it is doing', () => {
    render(<LoadingState label="Reading the audit log…" />);

    expect(screen.getByText('Reading the audit log…')).toBeTruthy();
  });

  it('ErrorState shows the reason', () => {
    render(<ErrorState message="the kernel is not reachable" />);

    expect(screen.getByText('the kernel is not reachable')).toBeTruthy();
  });

  it('ErrorState retries on demand', async () => {
    const onRetry = vi.fn();
    render(<ErrorState message="failed" onRetry={onRetry} />);

    await userEvent.click(screen.getByRole('button', { name: 'Try again' }));

    expect(onRetry).toHaveBeenCalledOnce();
  });

  it('ErrorState omits the retry button when there is nothing to retry', () => {
    render(<ErrorState message="failed" />);

    expect(screen.queryByRole('button')).toBeNull();
  });

  it('EmptyState renders a call to action', async () => {
    const onClick = vi.fn();
    render(
      <EmptyState
        title="No models"
        message="Add one to begin."
        action={<Button onClick={onClick}>Add</Button>}
      />,
    );

    await userEvent.click(screen.getByRole('button', { name: 'Add' }));

    expect(screen.getByText('No models')).toBeTruthy();
    expect(onClick).toHaveBeenCalledOnce();
  });
});

describe('StatusPill', () => {
  it('falls back to the status as its label', () => {
    render(<StatusPill status="running" />);

    expect(screen.getByText('running')).toBeTruthy();
  });

  it('prefers an explicit label', () => {
    render(<StatusPill status="stopped" label="unavailable" />);

    expect(screen.getByText('unavailable')).toBeTruthy();
  });

  it.each([
    ['running', 'healthy'],
    ['error', 'failed'],
  ])('maps %s and its alias %s to the same colour', (status, alias) => {
    const { container: first } = render(<StatusPill status={status} />);
    const { container: second } = render(<StatusPill status={alias} />);

    const colourOf = (el: HTMLElement) =>
      (el.querySelector('span') as HTMLElement).style.color;

    expect(colourOf(first)).toBe(colourOf(second));
  });

  it('does not crash on an unknown status', () => {
    render(<StatusPill status="something-new" />);

    expect(screen.getByText('something-new')).toBeTruthy();
  });
});

describe('Mark', () => {
  it('is labelled for screen readers', () => {
    render(<Mark />);

    expect(screen.getByRole('img', { name: 'AERA' })).toBeTruthy();
  });

  it('drops the signal arcs when small', () => {
    // Below ~28px the arcs collapse into noise, matching the raster icons.
    const { container: small } = render(<Mark size={16} />);
    const { container: large } = render(<Mark size={64} />);

    expect(small.querySelectorAll('path').length).toBeLessThan(
      large.querySelectorAll('path').length,
    );
  });

  it('keeps the eye and pupil at every size', () => {
    const { container } = render(<Mark size={16} />);

    // ring, iris, pupil
    expect(container.querySelectorAll('circle').length).toBe(3);
  });

  it('scales without touching the viewBox', () => {
    const { container } = render(<Mark size={128} />);
    const svg = container.querySelector('svg')!;

    expect(svg.getAttribute('viewBox')).toBe('0 0 100 100');
    expect(svg.getAttribute('width')).toBe('128');
  });
});

describe('Card', () => {
  it('renders its title and children', () => {
    render(
      <Card title="Status">
        <p>All good</p>
      </Card>,
    );

    expect(screen.getByText('Status')).toBeTruthy();
    expect(screen.getByText('All good')).toBeTruthy();
  });

  it('is clickable when interactive', async () => {
    const onClick = vi.fn();
    const { container } = render(
      <Card interactive onClick={onClick}>
        pick me
      </Card>,
    );

    await userEvent.click(within(container).getByText('pick me'));

    expect(onClick).toHaveBeenCalledOnce();
  });
});

describe('Input', () => {
  it('reports what the user types', async () => {
    const onChange = vi.fn();
    render(<Input value="" onChange={onChange} placeholder="search" />);

    await userEvent.type(screen.getByPlaceholderText('search'), 'abc');

    expect(onChange).toHaveBeenCalledTimes(3);
  });

  it('honours disabled', async () => {
    const onChange = vi.fn();
    render(<Input value="" onChange={onChange} placeholder="search" disabled />);

    await userEvent.type(screen.getByPlaceholderText('search'), 'abc');

    expect(onChange).not.toHaveBeenCalled();
  });
});
