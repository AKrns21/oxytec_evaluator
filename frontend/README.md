# Oxytec Feasibility Platform - Frontend

Next.js 14 frontend for the Oxytec Multi-Agent Feasibility Platform.

## Features

- **Document Upload**: Drag-and-drop interface for uploading PDFs, Word docs, Excel files
- **Real-time Monitoring**: SSE-based live updates of agent execution
- **Agent Visualization**: Visual representation of the multi-agent workflow
- **Report Viewer**: Markdown-rendered feasibility reports with download capability
- **Responsive Design**: Modern UI built with Tailwind CSS and shadcn/ui

## Quick Start

### Prerequisites

- Node.js 18+
- Backend running on `http://localhost:8000`

### Installation

```bash
cd frontend

# Install dependencies
npm install

# Set up environment
cp .env.local.example .env.local

# Start development server
npm run dev
```

The application will be available at `http://localhost:3000`

### Building for Production

```bash
# Build
npm run build

# Start production server
npm start
```

### Using Docker

```bash
# Build image
docker build -t oxytec-frontend .

# Run container
docker run -p 3000:3000 -e NEXT_PUBLIC_API_URL=http://localhost:8000 oxytec-frontend
```

## Project Structure

```
frontend/
├── app/
│   ├── layout.tsx           # Root layout with navigation
│   ├── page.tsx             # Home page with upload form
│   ├── globals.css          # Global styles and Tailwind
│   └── session/
│       └── [id]/
│           └── page.tsx     # Session monitoring page
├── components/
│   ├── ui/                  # shadcn/ui components
│   ├── FileUpload.tsx       # Drag-and-drop file upload
│   ├── AgentVisualization.tsx  # Agent workflow display
│   └── ResultsViewer.tsx    # Report display with markdown
├── hooks/
│   └── useSSE.ts            # Server-Sent Events hook
├── lib/
│   └── utils.ts             # Utility functions
└── public/                  # Static assets
```

## Key Components

### FileUpload

Drag-and-drop file upload component supporting:
- PDF, DOCX, XLSX, CSV, TXT files
- Multiple file selection
- File size display
- Remove files

### AgentVisualization

Real-time visualization showing:
- Current agent execution stage
- Agent status (pending/running/completed)
- Progress through workflow
- Parallel subagent execution indication

### ResultsViewer

Displays the final report with:
- Markdown rendering
- Download functionality
- Statistics (agents used, errors, warnings)
- Structured report sections

### useSSE Hook

Custom hook for Server-Sent Events:
- Automatic connection management
- Event parsing and state updates
- Error handling
- Connection cleanup

## Configuration

### Environment Variables

Create `.env.local` file:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### API Integration

All API calls go through the backend at `NEXT_PUBLIC_API_URL`:

- `POST /api/sessions/create` - Create new feasibility study
- `GET /api/sessions/{id}` - Get session status
- `GET /api/sessions/{id}/stream` - SSE endpoint for real-time updates

## Development

### Type Checking

```bash
npm run type-check
```

### Linting

```bash
npm run lint
```

### Adding New Components

This project uses shadcn/ui. To add a new component:

1. Copy component from [shadcn/ui](https://ui.shadcn.com)
2. Place in `components/ui/`
3. Import and use

## Troubleshooting

### Connection Issues

If you see connection errors:
1. Ensure backend is running on port 8000
2. Check `NEXT_PUBLIC_API_URL` in `.env.local`
3. Verify CORS settings in backend

### SSE Not Connecting

- Check browser console for errors
- Verify session ID is valid
- Ensure backend SSE endpoint is accessible

### Build Errors

```bash
# Clean and reinstall
rm -rf .next node_modules
npm install
npm run build
```

## Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)

## Performance

- Server-Side Rendering for fast initial load
- Code splitting for optimal bundle size
- Optimized images and assets
- Real-time updates without polling

---

Built with Next.js 14, TypeScript, Tailwind CSS, and shadcn/ui
