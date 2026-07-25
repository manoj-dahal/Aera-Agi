import { useState } from 'react';
import { Download, FolderOpen, Globe, RefreshCw, Search } from 'lucide-react';
import { Button, Card, EmptyState, Input, PageHeader, Tag, useToast } from '@components/index';
import { workspace } from '@services/api';
import { detectHost } from '@services/transport';
import { cn } from '@utils/cn';

type Filter = 'recent' | 'images' | 'videos' | 'favorites' | 'folders';

const FILTERS: Array<[Filter, string]> = [
  ['recent', 'Recent'],
  ['images', 'Images'],
  ['videos', 'Videos'],
  ['favorites', 'Favorites'],
  ['folders', 'Local Folders'],
];

const IMAGE_EXT = /\.(png|jpe?g|gif|webp|bmp|svg|avif)$/i;
const VIDEO_EXT = /\.(mp4|mov|mkv|webm|avi|m4v)$/i;

/**
 * Gallery: media browsing and analysis (docs/11-GALLERY.md).
 *
 * Deliberately minimal, per the requirements: browse and analyse only. The
 * Browse button opens a small panel for downloading media from the web, which
 * is the one addition that was asked for.
 */
export function GalleryHome() {
  const [filter, setFilter] = useState<Filter>('recent');
  const [query, setQuery] = useState('');
  const [media, setMedia] = useState<string[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [browserOpen, setBrowserOpen] = useState(false);
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const showToast = useToast((s) => s.show);
  const isDesktop = detectHost() === 'desktop';

  /** Scan the open project for media files. */
  const scan = async () => {
    setLoading(true);
    try {
      const { files } = await workspace.tree(2000);
      setMedia(files.filter((f) => IMAGE_EXT.test(f) || VIDEO_EXT.test(f)));
    } catch {
      showToast('Open a folder first', 'error');
      setMedia([]);
    } finally {
      setLoading(false);
    }
  };

  const openFolder = async () => {
    if (!isDesktop) return showToast('Folder picker requires the desktop app', 'error');
    try {
      await workspace.openDialog();
      await scan();
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'could not open folder', 'error');
    }
  };

  const visible = media.filter((path) => {
    if (query.trim() && !path.toLowerCase().includes(query.toLowerCase())) return false;
    if (filter === 'images') return IMAGE_EXT.test(path);
    if (filter === 'videos') return VIDEO_EXT.test(path);
    return true;
  });

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto p-4">
      <PageHeader
        title="Gallery"
        subtitle="Browse and analyse local media"
        action={
          <div className="flex gap-2">
            <Button variant="ghost" icon={<Globe size={13} />} onClick={() => setBrowserOpen((v) => !v)}>
              Browse
            </Button>
            <Button variant="ghost" icon={<RefreshCw size={13} />} onClick={() => void scan()}>
              Refresh
            </Button>
            <Button variant="primary" icon={<FolderOpen size={14} />} onClick={() => void openFolder()}>
              Open Local Folder
            </Button>
          </div>
        }
      />

      {/* Small web browser panel: opens only on demand, for downloading media. */}
      {browserOpen && (
        <Card title="Download from the web" className="mb-3 max-w-2xl">
          <div className="flex gap-2">
            <Input
              value={url}
              placeholder="https://example.com/image.jpg"
              onChange={(e) => setUrl(e.target.value)}
            />
            <Button
              variant="primary"
              icon={<Download size={13} />}
              onClick={() => showToast('Media download requires the Web Agent, which is not built yet', 'error')}
            >
              Download
            </Button>
            <Button variant="ghost" onClick={() => setBrowserOpen(false)}>
              Close
            </Button>
          </div>
          <p className="mt-2 text-[11px] text-[var(--aera-text-disabled)]">
            Fetching remote media needs a Web Agent with network permission. The panel is
            here; the downloader is not implemented.
          </p>
        </Card>
      )}

      <div className="mb-3 flex flex-wrap items-center gap-2">
        <div className="relative max-w-xs flex-1">
          <Search
            size={13}
            className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[var(--aera-text-disabled)]"
          />
          <Input
            value={query}
            placeholder="Search media…"
            onChange={(e) => setQuery(e.target.value)}
            className="!pl-8"
          />
        </div>
        {FILTERS.map(([id, label]) => (
          <button
            key={id}
            onClick={() => setFilter(id)}
            className={cn(
              'rounded-md border px-2.5 py-1 text-[11.5px] transition-colors',
              filter === id
                ? 'border-[var(--aera-accent-primary)] text-[var(--aera-accent-primary)]'
                : 'border-[var(--aera-line-default)] text-[var(--aera-text-muted)] hover:text-[var(--aera-text-primary)]',
            )}
          >
            {label}
          </button>
        ))}
      </div>

      {visible.length === 0 ? (
        <EmptyState
          title={loading ? 'Scanning…' : 'No media found'}
          message={
            media.length === 0
              ? 'Open a local folder to index its images and videos.'
              : 'Nothing matches the current search or filter.'
          }
        />
      ) : (
        <div className="grid gap-2 [grid-template-columns:repeat(auto-fill,minmax(140px,1fr))]">
          {visible.slice(0, 200).map((path) => (
            <button
              key={path}
              onClick={() => setSelected(path)}
              className={cn(
                'group flex aspect-square flex-col items-center justify-center gap-1.5 rounded-lg border bg-[var(--aera-bg-surface)] p-2 transition-colors',
                selected === path
                  ? 'border-[var(--aera-accent-primary)]'
                  : 'border-[var(--aera-line-default)] hover:border-[var(--aera-line-strong)]',
              )}
            >
              <span className="text-[22px] opacity-60">{VIDEO_EXT.test(path) ? '▶' : '▣'}</span>
              <span className="w-full break-all text-center font-mono text-[9.5px] leading-tight text-[var(--aera-text-muted)]">
                {path.split('/').pop()}
              </span>
            </button>
          ))}
        </div>
      )}

      {selected && (
        <Card title="Preview" className="mt-3 max-w-2xl">
          <p className="selectable break-all font-mono text-[11px]">{selected}</p>
          <div className="mt-2 flex gap-1.5">
            <Tag>{VIDEO_EXT.test(selected) ? 'video' : 'image'}</Tag>
            <Button
              size="sm"
              variant="ghost"
              className="ml-auto"
              onClick={() => showToast('Media analysis needs the Vision Agent, which is not built yet', 'error')}
            >
              Analyse
            </Button>
          </div>
        </Card>
      )}
    </div>
  );
}

export default GalleryHome;
