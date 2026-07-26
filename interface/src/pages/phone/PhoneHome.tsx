/*
 * MADE By Manoj Dahal
 * Copyright (c) 2026 Manoj Dahal. All rights reserved.
 * Contact: info@manoj-dahal.com.np
 * AERA — Artificial Voice Reasoning Assistant
 */

import { useState } from 'react';
import { Battery, Bell, MessageSquare, Send, Smartphone, Wifi } from 'lucide-react';
import { Button, Card, EmptyState, KeyValue, PageHeader, StatusPill, useToast } from '@components/index';

/**
 * Phone: the device hub (docs/12-PHONE.md).
 *
 * Device management only — the requirements explicitly moved drag & drop off
 * this page and onto the Dashboard transcript watermark.
 */
export function PhoneHome() {
  const [pairing, setPairing] = useState(false);
  const showToast = useToast((s) => s.show);

  const notImplemented = (what: string) =>
    showToast(`${what} requires the Device Agent, which is not built yet`, 'error');

  const capabilities = [
    { Icon: Bell, label: 'Notifications', hint: 'Mirror phone notifications' },
    { Icon: MessageSquare, label: 'Messages', hint: 'Read and reply to SMS' },
    { Icon: Send, label: 'File transfer', hint: 'Send files between devices' },
    { Icon: Battery, label: 'Battery & storage', hint: 'Device status at a glance' },
  ];

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto p-4">
      <PageHeader
        title="Phone"
        subtitle="Connect and manage mobile devices"
        action={
          <Button
            variant="primary"
            icon={<Smartphone size={14} />}
            loading={pairing}
            onClick={() => {
              setPairing(true);
              setTimeout(() => {
                setPairing(false);
                notImplemented('Device pairing');
              }, 700);
            }}
          >
            Pair Device
          </Button>
        }
      />

      <Card title="Connected devices" className="mb-3 max-w-2xl">
        <EmptyState
          message="No devices paired. Pairing needs the Device Agent and a companion app on the phone; neither ships in this build."
        />
      </Card>

      <h3 className="mb-2 text-[10.5px] uppercase tracking-[0.11em] text-[var(--aera-text-muted)]">
        Planned capabilities
      </h3>
      <div className="grid max-w-3xl gap-2 [grid-template-columns:repeat(auto-fill,minmax(240px,1fr))]">
        {capabilities.map(({ Icon, label, hint }) => (
          <Card key={label}>
            <div className="flex items-start gap-2.5">
              <Icon size={16} strokeWidth={1.7} className="text-[var(--aera-text-disabled)]" />
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <h4 className="text-[12.5px] font-semibold">{label}</h4>
                  <StatusPill status="idle" label="planned" />
                </div>
                <p className="mt-0.5 text-[11px] text-[var(--aera-text-muted)]">{hint}</p>
              </div>
            </div>
          </Card>
        ))}
      </div>

      <Card title="How pairing will work" className="mt-3 max-w-2xl">
        <KeyValue label="Transport" value="Local network, no cloud relay" />
        <KeyValue label="Platforms" value="Android, iOS (within platform limits)" />
        <KeyValue label="Security" value="Paired-device tokens held in the encrypted vault" />
        <p className="mt-2 flex items-center gap-1.5 text-[11px] text-[var(--aera-text-disabled)]">
          <Wifi size={11} />
          The REST API is already reachable from a phone on the same network.
        </p>
      </Card>
    </div>
  );
}

export default PhoneHome;
