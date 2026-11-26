import { fireEvent, render, screen } from '@testing-library/react';
import { createRef } from 'react';
import { describe, expect, it, vi } from 'vitest';
import { Button } from './button';

/**
 * Behaviour and accessibility contract of the shared `Button`.
 * Everything is queried the way a screen-reader user would reach it
 * (accessible role + accessible name), never by CSS class.
 *
 * Interactions use `fireEvent` from Testing Library so the suite needs no
 * extra dependency in `frontend/package.json` (this PR must not modify files
 * owned by PR #6). Browser-native key activation (Enter/Space → click) is a
 * jsdom limitation that `@testing-library/user-event` would emulate; it can
 * be added together with that dependency once the package.json change is
 * agreed with PR #6.
 */
describe('Button', () => {
  it('renders a native button with its accessible name', () => {
    render(<Button>Start Investigation</Button>);

    const button = screen.getByRole('button', { name: 'Start Investigation' });
    expect(button).toBeInTheDocument();
    expect(button.tagName).toBe('BUTTON');
  });

  it('defaults to type="button" so it cannot submit a form by accident', () => {
    render(<Button>Cancel</Button>);
    expect(screen.getByRole('button', { name: 'Cancel' })).toHaveAttribute('type', 'button');
  });

  it('honours an explicit type="submit"', () => {
    render(<Button type="submit">Start Investigation</Button>);
    expect(screen.getByRole('button', { name: 'Start Investigation' })).toHaveAttribute(
      'type',
      'submit',
    );
  });

  it('calls onClick once per click', () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Retry</Button>);

    fireEvent.click(screen.getByRole('button', { name: 'Retry' }));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it('is focusable and activatable', () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Retry</Button>);

    const button = screen.getByRole('button', { name: 'Retry' });
    button.focus();
    expect(button).toHaveFocus();

    // Activation semantics: clicking the focused button reaches onClick once.
    fireEvent.click(button);
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it('does not fire onClick when disabled and exposes the disabled state', () => {
    const onClick = vi.fn();
    render(
      <Button disabled onClick={onClick}>
        Start Investigation
      </Button>,
    );

    const button = screen.getByRole('button', { name: 'Start Investigation' });
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute('disabled');

    // Native activation honours the disabled attribute: no click reaches the
    // handler (HTMLElement#click() terminates on disabled form controls).
    button.click();
    expect(onClick).not.toHaveBeenCalled();
  });

  it('announces busy work through aria-busy', () => {
    render(<Button aria-busy="true">Loading…</Button>);
    expect(screen.getByRole('button', { name: 'Loading…' })).toHaveAttribute('aria-busy', 'true');
  });

  it('exposes an accessible name given through aria-label', () => {
    render(
      <Button aria-label="Switch theme">
        <span aria-hidden="true">🌙</span>
      </Button>,
    );
    expect(screen.getByRole('button', { name: 'Switch theme' })).toBeInTheDocument();
  });

  it('keeps icons decorative-only when they are marked aria-hidden', () => {
    render(
      <Button aria-label="Skip to content">
        <svg aria-hidden="true" data-testid="chevron" />
        Continue
      </Button>,
    );
    const button = screen.getByRole('button', { name: 'Skip to content' });
    // The visible text ("Continue") is overridden by the explicit label, which
    // is the expected, announced name.
    expect(button).toHaveAccessibleName('Skip to content');
    // Decorative children stay hidden from assistive technology.
    expect(screen.getByTestId('chevron')).toHaveAttribute('aria-hidden', 'true');
  });

  it('forwards the ref to the underlying DOM node and merges className', () => {
    const ref = createRef<HTMLButtonElement>();
    render(
      <Button ref={ref} className="custom-class">
        Retry
      </Button>,
    );

    expect(ref.current).toBeInstanceOf(HTMLButtonElement);
    expect(ref.current).toBe(screen.getByRole('button', { name: 'Retry' }));
    expect(ref.current).toHaveClass('custom-class');
  });

  it('renders without crashing for every variant and size', () => {
    const variants = ['default', 'secondary', 'outline', 'ghost', 'destructive'] as const;
    const sizes = ['default', 'sm', 'lg'] as const;

    for (const variant of variants) {
      for (const size of sizes) {
        const { unmount } = render(
          <Button variant={variant} size={size}>
            {`${variant}-${size}`}
          </Button>,
        );
        expect(
          screen.getByRole('button', { name: `${variant}-${size}` }),
        ).toBeInTheDocument();
        unmount();
      }
    }
  });

  it('shows an error state through the documented destructive variant', () => {
    render(<Button variant="destructive">Delete investigation</Button>);
    const button = screen.getByRole('button', { name: 'Delete investigation' });
    expect(button).toHaveClass('bg-destructive');
  });
});
