import { PlannedFeature } from '@components/widgets/PlannedFeature';

export function DockerHome() {
  return (
    <PlannedFeature
      title="Docker"
      subtitle="Container, image and volume management"
      available={
        <>
          AERA itself ships a Dockerfile and a Compose stack, so the platform can run
          containerised today. The management API for inspecting other containers is
          not wired up.
        </>
      }
      planned={[
        'Container list, start, stop and logs',
        'Image and volume inspection',
        'Compose project control from the dashboard',
      ]}
      spec="docs/27-DOCKER.md, docs/docker/Containers.md"
    />
  );
}

export default DockerHome;
