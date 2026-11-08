import { useEffect, useRef } from 'react'
import { useTheme } from 'next-themes'
import { Toaster as Sonner, useSonner } from 'sonner'
import type { ToasterProps } from 'sonner'
import {
  CircleCheckIcon,
  InfoIcon,
  TriangleAlertIcon,
  OctagonXIcon,
  Loader2Icon,
} from 'lucide-react'

/** Fired when something enters the top layer (e.g. a modal) above the toaster. */
export const TOASTER_RAISE_EVENT = 'toaster:raise'

const Toaster = ({ ...props }: ToasterProps) => {
  const { theme = 'light' } = useTheme()
  const ref = useRef<HTMLElement>(null)
  const { toasts } = useSonner()

  useEffect(() => {
    const node = ref.current

    if (!node || typeof node.showPopover !== 'function') {
      return
    }

    const toaster = node

    // Toasts need to live in the browser's top layer. Native <dialog> modals
    // also live there, so a regular fixed element would paint behind them.
    toaster.setAttribute('popover', 'manual')

    function raise() {
      if (toasts.length === 0) {
        return
      }

      // Re-opening moves the toaster to the top of the top layer, above any
      // modal that was opened after the toast appeared.
      if (toaster.matches(':popover-open')) {
        toaster.hidePopover()
      }

      toaster.showPopover()
    }

    raise()
    document.addEventListener(TOASTER_RAISE_EVENT, raise)

    return () => {
      document.removeEventListener(TOASTER_RAISE_EVENT, raise)
    }
  }, [toasts.length])

  return (
    <Sonner
      ref={ref}
      theme={theme as ToasterProps['theme']}
      className="toaster group"
      icons={{
        success: <CircleCheckIcon className="size-4" />,
        info: <InfoIcon className="size-4" />,
        warning: <TriangleAlertIcon className="size-4" />,
        error: <OctagonXIcon className="size-4" />,
        loading: <Loader2Icon className="size-4 animate-spin" />,
      }}
      style={
        {
          '--normal-bg': 'var(--popover)',
          '--normal-text': 'var(--popover-foreground)',
          '--normal-border': 'var(--border)',
          '--border-radius': 'var(--radius)',
        } as React.CSSProperties
      }
      toastOptions={{
        classNames: {
          toast: 'cn-toast',
        },
      }}
      {...props}
    />
  )
}

export { Toaster }
