import { PlannedFeature } from '@components/widgets/PlannedFeature';

export function GalleryHome() {
  return (
    <PlannedFeature
      title="Gallery"
      subtitle="AI-indexed media library"
      available={
        <>
          Files dropped onto the Dashboard transcript are routed to an agent and recorded
          in the memory graph, so media already becomes part of AERA's context. The
          browsing surface and thumbnail pipeline are not built.
        </>
      }
      planned={[
        'Image, video and audio grid with thumbnails',
        'Vision-model tagging and semantic media search',
        'Favourites, collections and background indexing',
      ]}
      spec="docs/11-GALLERY.md"
    />
  );
}

export default GalleryHome;
