import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { RouterProvider } from '@tanstack/react-router'

import { getRouter } from './router'

const router = getRouter()
const rootElement = document.getElementById('app')

if (!rootElement) {
  throw new Error('Elemento #app não encontrado.')
}

if (!rootElement.innerHTML) {
  createRoot(rootElement).render(
    <StrictMode>
      <RouterProvider router={router} />
    </StrictMode>,
  )
}
