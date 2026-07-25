import { PlannedFeature } from '@components/widgets/PlannedFeature';

export function PhoneHome() {
  return (
    <PlannedFeature
      title="Phone"
      subtitle="Mobile device integration"
      available={
        <>
          The event bus and notification agent already carry the message types a paired
          device would produce, and the REST API is reachable from a phone on the same
          network.
        </>
      }
      planned={[
        'Android and iOS pairing over the local network',
        'Notification, SMS and call mirroring',
        'File transfer and clipboard sync',
      ]}
      spec="docs/12-PHONE.md"
    />
  );
}

export default PhoneHome;
